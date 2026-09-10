<?php if (!defined('ABSPATH')) { exit; } ?>
<?php if (!empty($route_links) && is_array($route_links)) : ?>
<nav class="kklidi-members-form-links kklidi-members-form-links--inline" aria-label="<?php esc_attr_e('Account links', 'kklidi-members'); ?>">
	<?php foreach ($route_links as $index => $route_link) : ?>
		<?php if ($index > 0) : ?><span class="kklidi-members-form-links__separator" aria-hidden="true">|</span><?php endif; ?>
		<a href="<?php echo esc_url($route_link['url']); ?>"><?php echo esc_html($route_link['label']); ?></a>
	<?php endforeach; ?>
</nav>
<?php endif; ?>
