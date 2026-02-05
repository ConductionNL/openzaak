<template>
	<div id="openzaak-app">
		<NcEmptyContent
			:name="t('openzaak', 'OpenZaak')"
			:description="t('openzaak', 'ZGW case management integration for Nextcloud')">
			<template #icon>
				<FolderPlusIcon :size="64" />
			</template>
		</NcEmptyContent>
	</div>
</template>

<script>
import { NcEmptyContent } from '@nextcloud/vue'
import FolderPlusIcon from 'vue-material-design-icons/FolderPlus.vue'

export default {
	name: 'App',
	components: {
		NcEmptyContent,
		FolderPlusIcon,
	},
}
</script>
