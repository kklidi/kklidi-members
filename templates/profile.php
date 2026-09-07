<?php if (!defined('ABSPATH')) { exit; } ?>
<!doctype html><html <?php language_attributes(); ?>><head>
<meta charset="<?php bloginfo('charset'); ?>"><meta name="viewport" content="width=device-width, initial-scale=1"><meta name="robots" content="noindex,nofollow"><title><?php esc_html_e('Profile', 'kklidi-members'); ?></title><?php wp_head(); ?>
</head><body <?php body_class('kklidi-members-page kklidi-members-page--profile'); ?>><?php wp_body_open(); ?>
<main class="kklidi-members-main"><section class="kklidi-members-card" aria-labelledby="kklidi-members-page-title"><header class="kklidi-members-header"><h1 id="kklidi-members-page-title"><?php esc_html_e('Profile', 'kklidi-members'); ?></h1></header>
<?php if ($message !== '') : ?><p class="kklidi-members-notice" role="status"><?php echo esc_html($message); ?></p><?php endif; ?>
<form class="kklidi-members-form" method="post"><input type="hidden" name="kklidi_members_profile" value="1"><?php wp_nonce_field('kklidi_members_profile', '_kklidi_members_profile_nonce'); ?>
<label class="kklidi-members-field"><?php esc_html_e('Email', 'kklidi-members'); ?><input type="email" value="<?php echo esc_attr($user->user_email); ?>" readonly></label>
<label class="kklidi-members-field"><?php esc_html_e('First name', 'kklidi-members'); ?><input name="first_name" autocomplete="given-name" value="<?php echo esc_attr($user->first_name); ?>"></label>
<label class="kklidi-members-field"><?php esc_html_e('Last name', 'kklidi-members'); ?><input name="last_name" autocomplete="family-name" value="<?php echo esc_attr($user->last_name); ?>"></label>
<label class="kklidi-members-field"><?php esc_html_e('Display name', 'kklidi-members'); ?><input name="display_name" autocomplete="nickname" value="<?php echo esc_attr($user->display_name); ?>" required></label>
<label class="kklidi-members-field"><?php esc_html_e('Phone', 'kklidi-members'); ?><input name="phone" autocomplete="tel" value="<?php echo esc_attr($phone); ?>" inputmode="tel"></label>
<label class="kklidi-members-field"><?php esc_html_e('Bio', 'kklidi-members'); ?><textarea name="description"><?php echo esc_textarea($user->description); ?></textarea></label>
<button class="kklidi-members-button" type="submit"><?php esc_html_e('Save', 'kklidi-members'); ?></button></form>
</section></main><?php wp_footer(); ?></body></html>
