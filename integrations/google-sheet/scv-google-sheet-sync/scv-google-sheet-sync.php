<?php
/**
 * Plugin Name:       SCV – Commandes vers Google Sheet
 * Description:       Envoie automatiquement chaque commande WooCommerce (une ligne par sortie / produit) vers un Google Sheet via un webhook Google Apps Script.
 * Version:           1.0.0
 * Author:            Ski Club Vence
 * Requires PHP:      7.4
 * Requires Plugins:  woocommerce
 * Text Domain:       scv-sheet
 */

defined( 'ABSPATH' ) || exit;

final class SCV_Google_Sheet_Sync {

	const OPTION        = 'scv_sheet_settings';
	const META_SENT     = '_scv_sheet_last_sync';
	const ACTION_HOOK   = 'scv_sheet_send_order';
	const LOG_SOURCE    = 'scv-google-sheet';

	/** Statuts transmis au Google Sheet (les autres — brouillon, en attente de paiement — sont ignorés). */
	const SYNCED_STATUSES = array( 'processing', 'completed', 'on-hold', 'cancelled', 'refunded', 'failed' );

	public static function init() {
		// Paiement validé (Monetico) ou commande créée manuellement.
		add_action( 'woocommerce_payment_complete', array( __CLASS__, 'queue' ), 20 );
		// Tout changement de statut ultérieur (annulation, remboursement…) met à jour les lignes existantes.
		add_action( 'woocommerce_order_status_changed', array( __CLASS__, 'on_status_changed' ), 20, 4 );
		// Envoi différé (Action Scheduler) pour ne jamais ralentir la page de paiement.
		add_action( self::ACTION_HOOK, array( __CLASS__, 'send' ) );

		// Action manuelle dans l'écran de la commande : « Envoyer vers le Google Sheet ».
		add_filter( 'woocommerce_order_actions', array( __CLASS__, 'order_action' ) );
		add_action( 'woocommerce_order_action_scv_sheet_resend', array( __CLASS__, 'manual_resend' ) );

		// Réglages : Réglages > Google Sheet SCV.
		add_action( 'admin_menu', array( __CLASS__, 'admin_menu' ) );
		add_action( 'admin_init', array( __CLASS__, 'register_settings' ) );
		add_action( 'admin_post_scv_sheet_test', array( __CLASS__, 'send_test' ) );
	}

	/* ------------------------------------------------------------------ */
	/* Déclencheurs                                                        */
	/* ------------------------------------------------------------------ */

	public static function on_status_changed( $order_id, $from, $to, $order ) {
		if ( in_array( $to, self::SYNCED_STATUSES, true ) ) {
			self::queue( $order_id );
		}
	}

	public static function queue( $order_id ) {
		$order_id = absint( $order_id );
		if ( ! $order_id || ! self::webhook_url() ) {
			return;
		}
		if ( function_exists( 'as_enqueue_async_action' ) ) {
			// Un seul envoi en attente par commande (évite les doublons si plusieurs hooks se déclenchent).
			if ( ! as_has_scheduled_action( self::ACTION_HOOK, array( $order_id ), 'scv-sheet' ) ) {
				as_enqueue_async_action( self::ACTION_HOOK, array( $order_id ), 'scv-sheet' );
			}
			return;
		}
		self::send( $order_id );
	}

	/* ------------------------------------------------------------------ */
	/* Construction et envoi du payload                                    */
	/* ------------------------------------------------------------------ */

	public static function send( $order_id ) {
		$order = wc_get_order( $order_id );
		if ( ! $order || 'shop_order_refund' === $order->get_type() ) {
			return false;
		}
		$status = $order->get_status();
		if ( ! in_array( $status, self::SYNCED_STATUSES, true ) ) {
			return false;
		}
		return self::post( self::build_payload( $order ), $order );
	}

	public static function build_payload( WC_Order $order ) {
		$created = $order->get_date_created();
		$items   = array();

		foreach ( $order->get_items() as $item_id => $item ) {
			/** @var WC_Order_Item_Product $item */
			$product   = $item->get_product();
			$parent_id = $item->get_product_id();
			$formule   = array();

			// Attributs de variation (ex. « Formule : Enfant (-18 ans) – forfait + cours + goûter »).
			foreach ( $item->get_formatted_meta_data( '_', true ) as $meta ) {
				$formule[] = wp_strip_all_tags( $meta->display_key ) . ' : ' . wp_strip_all_tags( $meta->display_value );
			}

			$items[] = array(
				'item_id'      => $item_id,
				'product_id'   => $parent_id,
				'variation_id' => $item->get_variation_id(),
				// Nom du produit parent = nom de la sortie (sert de clé de filtre et de nom d'onglet).
				'product'      => html_entity_decode( get_the_title( $parent_id ) ?: $item->get_name(), ENT_QUOTES, 'UTF-8' ),
				'formule'      => implode( ' | ', $formule ),
				'sku'          => $product ? $product->get_sku() : '',
				'category'     => $parent_id ? wp_strip_all_tags( wc_get_product_category_list( $parent_id, ', ' ) ) : '',
				'quantity'     => (int) $item->get_quantity(),
				'total'        => (float) wc_format_decimal( $item->get_total() + $item->get_total_tax(), 2 ),
			);
		}

		return array(
			'secret' => self::secret(),
			'event'  => current_action(),
			'site'   => home_url(),
			'order'  => array(
				'id'             => $order->get_id(),
				'number'         => $order->get_order_number(),
				'date'           => $created ? $created->date_i18n( 'Y-m-d H:i:s' ) : '',
				'status'         => $order->get_status(),
				'status_label'   => wc_get_order_status_name( $order->get_status() ),
				'first_name'     => $order->get_billing_first_name(),
				'last_name'      => $order->get_billing_last_name(),
				'email'          => $order->get_billing_email(),
				'phone'          => $order->get_billing_phone(),
				'payment_method' => $order->get_payment_method_title(),
				'total'          => (float) wc_format_decimal( $order->get_total(), 2 ),
				'currency'       => $order->get_currency(),
				'note'           => $order->get_customer_note(),
				'edit_url'       => $order->get_edit_order_url(),
			),
			'items'  => $items,
		);
	}

	private static function post( array $payload, $order = null ) {
		$url = self::webhook_url();
		if ( ! $url ) {
			return false;
		}
		$response = wp_remote_post(
			$url,
			array(
				'timeout'     => 20,
				// Apps Script exécute doPost puis répond par une redirection 302 vers la réponse JSON : on la suit pour la lire.
				'redirection' => 3,
				'headers'     => array( 'Content-Type' => 'application/json; charset=utf-8' ),
				'body'        => wp_json_encode( $payload ),
				'data_format' => 'body',
			)
		);

		$code = is_wp_error( $response ) ? 0 : (int) wp_remote_retrieve_response_code( $response );
		$body = is_wp_error( $response ) ? $response->get_error_message() : wp_remote_retrieve_body( $response );
		$json = json_decode( (string) $body, true );
		// Succès uniquement si le script a confirmé l'écriture ({"ok":true}) : protège contre une mauvaise URL ou clé secrète.
		$ok   = 200 === $code && is_array( $json ) && ! empty( $json['ok'] );

		$logger = wc_get_logger();
		if ( $ok ) {
			$logger->info( sprintf( 'Commande #%s envoyée (%d ligne(s)).', $payload['order']['number'], count( $payload['items'] ) ), array( 'source' => self::LOG_SOURCE ) );
			if ( $order ) {
				$order->update_meta_data( self::META_SENT, current_time( 'mysql' ) . ' — ' . $order->get_status() );
				$order->save_meta_data();
			}
		} else {
			$logger->error( sprintf( 'Échec de l\'envoi de la commande #%s (HTTP %d) : %s', $payload['order']['number'], $code, mb_substr( (string) $body, 0, 500 ) ), array( 'source' => self::LOG_SOURCE ) );
			if ( $order ) {
				$order->add_order_note( 'Google Sheet : échec de l\'envoi (HTTP ' . $code . '). Utilisez l\'action « Envoyer vers le Google Sheet » pour réessayer.' );
			}
			// Dans Action Scheduler, une exception marque l'action en échec (visible dans Outils > Actions planifiées).
			if ( doing_action( self::ACTION_HOOK ) ) {
				throw new Exception( 'SCV Google Sheet : envoi échoué (HTTP ' . $code . ')' );
			}
		}
		return $ok;
	}

	/* ------------------------------------------------------------------ */
	/* Action manuelle sur la commande                                     */
	/* ------------------------------------------------------------------ */

	public static function order_action( $actions ) {
		$actions['scv_sheet_resend'] = 'Envoyer vers le Google Sheet';
		return $actions;
	}

	public static function manual_resend( $order ) {
		$ok = self::post( self::build_payload( $order ), $order );
		$order->add_order_note( $ok ? 'Google Sheet : commande renvoyée manuellement.' : 'Google Sheet : échec du renvoi manuel.' );
	}

	/* ------------------------------------------------------------------ */
	/* Réglages                                                            */
	/* ------------------------------------------------------------------ */

	private static function settings() {
		return wp_parse_args( get_option( self::OPTION, array() ), array( 'url' => '', 'secret' => '' ) );
	}

	private static function webhook_url() {
		if ( defined( 'SCV_SHEET_WEBHOOK_URL' ) ) {
			return SCV_SHEET_WEBHOOK_URL;
		}
		return esc_url_raw( self::settings()['url'] );
	}

	private static function secret() {
		if ( defined( 'SCV_SHEET_SECRET' ) ) {
			return SCV_SHEET_SECRET;
		}
		return (string) self::settings()['secret'];
	}

	public static function admin_menu() {
		add_options_page( 'Google Sheet SCV', 'Google Sheet SCV', 'manage_woocommerce', 'scv-google-sheet', array( __CLASS__, 'render_settings' ) );
	}

	public static function register_settings() {
		register_setting(
			'scv_sheet',
			self::OPTION,
			array(
				'type'              => 'array',
				'sanitize_callback' => function ( $value ) {
					return array(
						'url'    => esc_url_raw( trim( $value['url'] ?? '' ) ),
						'secret' => sanitize_text_field( $value['secret'] ?? '' ),
					);
				},
			)
		);
	}

	public static function render_settings() {
		$s = self::settings();
		?>
		<div class="wrap">
			<h1>Commandes → Google Sheet</h1>
			<?php if ( isset( $_GET['scv_test'] ) ) : // phpcs:ignore WordPress.Security.NonceVerification ?>
				<div class="notice notice-<?php echo '1' === $_GET['scv_test'] ? 'success' : 'error'; // phpcs:ignore ?>"><p>
					<?php echo '1' === $_GET['scv_test'] ? 'Test réussi : une ligne « TEST » a été ajoutée au Google Sheet.' : 'Le test a échoué. Consultez WooCommerce > État > Journaux (source scv-google-sheet).'; // phpcs:ignore ?>
				</p></div>
			<?php endif; ?>
			<form method="post" action="options.php">
				<?php settings_fields( 'scv_sheet' ); ?>
				<table class="form-table" role="presentation">
					<tr>
						<th scope="row"><label for="scv-url">URL du webhook Apps Script</label></th>
						<td><input id="scv-url" type="url" class="large-text" name="<?php echo esc_attr( self::OPTION ); ?>[url]" value="<?php echo esc_attr( $s['url'] ); ?>" placeholder="https://script.google.com/macros/s/…/exec" <?php disabled( defined( 'SCV_SHEET_WEBHOOK_URL' ) ); ?>></td>
					</tr>
					<tr>
						<th scope="row"><label for="scv-secret">Clé secrète</label></th>
						<td><input id="scv-secret" type="text" class="regular-text" name="<?php echo esc_attr( self::OPTION ); ?>[secret]" value="<?php echo esc_attr( $s['secret'] ); ?>" <?php disabled( defined( 'SCV_SHEET_SECRET' ) ); ?>>
						<p class="description">Doit être identique à la constante <code>SECRET</code> du script Google Apps Script.</p></td>
					</tr>
				</table>
				<?php submit_button( 'Enregistrer' ); ?>
			</form>
			<form method="post" action="<?php echo esc_url( admin_url( 'admin-post.php' ) ); ?>">
				<input type="hidden" name="action" value="scv_sheet_test">
				<?php wp_nonce_field( 'scv_sheet_test' ); ?>
				<?php submit_button( 'Envoyer une commande de test', 'secondary' ); ?>
			</form>
		</div>
		<?php
	}

	public static function send_test() {
		if ( ! current_user_can( 'manage_woocommerce' ) || ! check_admin_referer( 'scv_sheet_test' ) ) {
			wp_die( 'Accès refusé.' );
		}
		$payload = array(
			'secret' => self::secret(),
			'event'  => 'test',
			'site'   => home_url(),
			'order'  => array(
				'id' => 0, 'number' => 'TEST', 'date' => current_time( 'Y-m-d H:i:s' ), 'status' => 'test',
				'status_label' => 'Test', 'first_name' => 'Test', 'last_name' => 'Ski Club Vence',
				'email' => get_option( 'admin_email' ), 'phone' => '', 'payment_method' => 'Test', 'total' => 0,
				'currency' => 'EUR', 'note' => 'Ligne de test — peut être supprimée.', 'edit_url' => '',
			),
			'items'  => array(
				array( 'item_id' => 0, 'product_id' => 0, 'variation_id' => 0, 'product' => 'TEST', 'formule' => '', 'sku' => '', 'category' => '', 'quantity' => 1, 'total' => 0 ),
			),
		);
		$ok = self::post( $payload );
		wp_safe_redirect( admin_url( 'options-general.php?page=scv-google-sheet&scv_test=' . ( $ok ? '1' : '0' ) ) );
		exit;
	}
}

add_action( 'plugins_loaded', function () {
	if ( class_exists( 'WooCommerce' ) ) {
		SCV_Google_Sheet_Sync::init();
	}
} );
