<?php if (!defined('ABSPATH')) { exit; } ?>
<div class="wrap kklidi-members-admin">
	<h1><?php esc_html_e('KKLIDI Members', 'kklidi-members'); ?></h1>
	<nav class="nav-tab-wrapper" aria-label="<?php esc_attr_e('Members administration', 'kklidi-members'); ?>">
		<?php foreach ($sections as $section_key => $section_label) : ?>
			<a class="nav-tab <?php echo $section === $section_key ? 'nav-tab-active' : ''; ?>" href="<?php echo esc_url(add_query_arg(array('page' => 'kklidi-members', 'section' => $section_key), admin_url('users.php'))); ?>"><?php echo esc_html($section_label); ?></a>
		<?php endforeach; ?>
	</nav>

	<?php if (isset($_GET['notice']) && sanitize_key(wp_unslash($_GET['notice'])) === 'saved') : ?>
		<div class="notice notice-success is-dismissible" role="status"><p><?php esc_html_e('Settings saved.', 'kklidi-members'); ?></p></div>
	<?php elseif (isset($_GET['notice']) && sanitize_key(wp_unslash($_GET['notice'])) === 'withdrawal_updated') : ?>
		<div class="notice notice-success is-dismissible" role="status"><p><?php esc_html_e('Withdrawal status updated.', 'kklidi-members'); ?></p></div>
	<?php endif; ?>

	<?php if ($section === 'overview') : ?>
		<section class="kklidi-members-admin-card">
			<h2><?php esc_html_e('Overview', 'kklidi-members'); ?></h2>
			<p><?php esc_html_e('Review the current account-system prerequisites without changing WordPress or external plugin data.', 'kklidi-members'); ?></p>
			<div class="kklidi-members-diagnostics">
				<?php foreach ($overview as $item) : ?>
					<article class="kklidi-members-diagnostic">
						<h3><?php echo esc_html($item['label']); ?></h3>
						<p><span class="kklidi-members-status <?php echo $item['ready'] ? 'is-ready' : 'is-attention'; ?>"><?php echo esc_html($item['ready'] ? __('Ready', 'kklidi-members') : __('Needs attention', 'kklidi-members')); ?></span></p>
						<p><?php echo esc_html($item['detail']); ?></p>
					</article>
				<?php endforeach; ?>
			</div>
		</section>
	<?php elseif ($section === 'documents') : ?>
		<section class="kklidi-members-admin-card">
			<h2><?php esc_html_e('URL ownership', 'kklidi-members'); ?></h2>
			<p><?php esc_html_e('Public registration remains controlled by the WordPress General Settings screen.', 'kklidi-members'); ?></p>
			<form method="post">
				<?php wp_nonce_field('kklidi_members_admin', '_kklidi_members_admin_nonce'); ?>
				<input type="hidden" name="section" value="documents">
				<input type="hidden" name="kklidi_members_admin_action" value="save_url_settings">
				<p><label><input type="checkbox" name="own_login_url" value="1" <?php checked(get_option('kklidi_members_own_login_url'), '1'); ?>> <?php esc_html_e('Members owns the Core login URL', 'kklidi-members'); ?></label></p>
				<p><label><input type="checkbox" name="own_register_url" value="1" <?php checked(get_option('kklidi_members_own_register_url'), '1'); ?>> <?php esc_html_e('Members owns the Core registration URL', 'kklidi-members'); ?></label></p>
				<p><button class="button button-primary" type="submit"><?php esc_html_e('Save URL settings', 'kklidi-members'); ?></button></p>
			</form>
		</section>

		<?php foreach (array('service' => __('Service terms', 'kklidi-members'), 'privacy' => __('Privacy policy', 'kklidi-members'), 'marketing' => __('Optional marketing consent', 'kklidi-members')) as $type => $label) : $document = $documents[$type]; ?>
			<section class="kklidi-members-admin-card">
				<h2><?php echo esc_html($label); ?></h2>
				<?php if ($document !== array()) : ?>
					<p><strong><?php esc_html_e('Current version', 'kklidi-members'); ?>:</strong> <?php echo esc_html($document['version']); ?></p>
					<p><strong>SHA-256:</strong> <code><?php echo esc_html($document['hash']); ?></code></p>
				<?php else : ?>
					<p><?php esc_html_e('No published version.', 'kklidi-members'); ?></p>
				<?php endif; ?>
				<form method="post">
					<?php wp_nonce_field('kklidi_members_admin', '_kklidi_members_admin_nonce'); ?>
					<input type="hidden" name="section" value="documents">
					<p><label><?php esc_html_e('New version', 'kklidi-members'); ?> <input name="<?php echo esc_attr($type); ?>_version" value=""></label></p>
					<p><label><?php esc_html_e('New document content', 'kklidi-members'); ?><br><textarea class="large-text" rows="7" name="<?php echo esc_attr($type); ?>_content"></textarea></label></p>
					<p class="kklidi-members-button-row">
						<button class="button" type="submit" name="kklidi_members_admin_action" value="preview_document"><?php esc_html_e('Preview', 'kklidi-members'); ?></button>
						<button class="button button-primary" type="submit" name="kklidi_members_admin_action" value="publish_document"><?php esc_html_e('Publish new version', 'kklidi-members'); ?></button>
						<input type="hidden" name="document_type" value="<?php echo esc_attr($type); ?>">
					</p>
				</form>

				<?php if (is_array($document_preview) && $document_preview['type'] === $type) : $preview = $document_preview['result']; ?>
					<?php if (is_wp_error($preview)) : ?>
						<div class="notice notice-error inline" role="alert"><p><?php echo esc_html($preview->get_error_message()); ?></p></div>
					<?php else : ?>
						<div class="kklidi-members-document-preview">
							<h3><?php esc_html_e('Unpublished preview', 'kklidi-members'); ?></h3>
							<p><?php echo esc_html($preview['version']); ?> / <code><?php echo esc_html($preview['hash']); ?></code></p>
							<div><?php echo wp_kses_post($preview['content']); ?></div>
						</div>
					<?php endif; ?>
				<?php endif; ?>

				<h3><?php esc_html_e('Published history', 'kklidi-members'); ?></h3>
				<table class="widefat striped kklidi-members-admin-table">
					<thead><tr><th scope="col"><?php esc_html_e('Version', 'kklidi-members'); ?></th><th scope="col">SHA-256</th><th scope="col"><?php esc_html_e('Published at (UTC)', 'kklidi-members'); ?></th><th scope="col"><?php esc_html_e('Status', 'kklidi-members'); ?></th></tr></thead>
					<tbody>
					<?php foreach ($document_history[$type] as $history) : ?>
						<tr><td data-label="<?php esc_attr_e('Version', 'kklidi-members'); ?>"><?php echo esc_html($history['version']); ?></td><td data-label="SHA-256"><code><?php echo esc_html($history['hash']); ?></code></td><td data-label="<?php esc_attr_e('Published at (UTC)', 'kklidi-members'); ?>"><?php echo esc_html($history['created_at_utc'] ?? '—'); ?></td><td data-label="<?php esc_attr_e('Status', 'kklidi-members'); ?>"><?php echo $document !== array() && hash_equals((string) $document['hash'], (string) $history['hash']) ? esc_html__('Current', 'kklidi-members') : esc_html__('Previous', 'kklidi-members'); ?></td></tr>
					<?php endforeach; ?>
					<?php if (!$document_history[$type]) : ?><tr><td colspan="4"><?php esc_html_e('No published history.', 'kklidi-members'); ?></td></tr><?php endif; ?>
					</tbody>
				</table>
			</section>
		<?php endforeach; ?>
	<?php elseif ($section === 'withdrawals') : ?>
		<section class="kklidi-members-admin-card">
			<h2><?php esc_html_e('Pending withdrawals', 'kklidi-members'); ?></h2>
			<table class="widefat striped kklidi-members-admin-table"><thead><tr><th scope="col"><?php esc_html_e('User ID', 'kklidi-members'); ?></th><th scope="col"><?php esc_html_e('Display name', 'kklidi-members'); ?></th><th scope="col"><?php esc_html_e('Action', 'kklidi-members'); ?></th></tr></thead><tbody>
			<?php foreach ($queue as $queued_user) : ?><tr><td data-label="<?php esc_attr_e('User ID', 'kklidi-members'); ?>"><?php echo (int) $queued_user->ID; ?></td><td data-label="<?php esc_attr_e('Display name', 'kklidi-members'); ?>"><?php echo esc_html($queued_user->display_name); ?></td><td data-label="<?php esc_attr_e('Action', 'kklidi-members'); ?>"><form method="post"><?php wp_nonce_field('kklidi_members_admin', '_kklidi_members_admin_nonce'); ?><input type="hidden" name="section" value="withdrawals"><input type="hidden" name="kklidi_members_admin_action" value="finalize_withdrawal"><input type="hidden" name="user_id" value="<?php echo (int) $queued_user->ID; ?>"><button class="button" type="submit"><?php esc_html_e('Confirm login block', 'kklidi-members'); ?></button></form></td></tr><?php endforeach; ?>
			<?php if (!$queue) : ?><tr><td colspan="3"><?php esc_html_e('No pending requests.', 'kklidi-members'); ?></td></tr><?php endif; ?></tbody></table>
		</section>
	<?php else : ?>
		<section class="kklidi-members-admin-card">
			<h2><?php esc_html_e('Recent security events', 'kklidi-members'); ?></h2>
			<table class="widefat striped kklidi-members-admin-table"><thead><tr><th scope="col">ID</th><th scope="col"><?php esc_html_e('User ID', 'kklidi-members'); ?></th><th scope="col">UTC</th><th scope="col"><?php esc_html_e('Type', 'kklidi-members'); ?></th><th scope="col"><?php esc_html_e('Result', 'kklidi-members'); ?></th><th scope="col"><?php esc_html_e('Reason', 'kklidi-members'); ?></th></tr></thead><tbody>
			<?php foreach ($audit_rows as $row) : ?><tr><td data-label="ID"><?php echo (int) $row->id; ?></td><td data-label="<?php esc_attr_e('User ID', 'kklidi-members'); ?>"><?php echo $row->user_id ? (int) $row->user_id : '—'; ?></td><td data-label="UTC"><?php echo esc_html($row->occurred_at_utc); ?></td><td data-label="<?php esc_attr_e('Type', 'kklidi-members'); ?>"><?php echo esc_html($row->event_type); ?></td><td data-label="<?php esc_attr_e('Result', 'kklidi-members'); ?>"><?php echo esc_html($row->result); ?></td><td data-label="<?php esc_attr_e('Reason', 'kklidi-members'); ?>"><?php echo esc_html($row->reason_code); ?></td></tr><?php endforeach; ?>
			<?php if (!$audit_rows) : ?><tr><td colspan="6"><?php esc_html_e('No audit events.', 'kklidi-members'); ?></td></tr><?php endif; ?></tbody></table>
		</section>
	<?php endif; ?>
</div>
