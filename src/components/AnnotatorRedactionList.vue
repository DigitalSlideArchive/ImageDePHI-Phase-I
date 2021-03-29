<template>
  <div>
    <ul>
      <li v-for="geojsonFeature in geojson.features" :key="geojsonFeature.id">
        <AnnotatorRedactionListItem
          v-model:name="geojsonFeature.properties.name"
          v-model:description="geojsonFeature.properties.description"
        >
        </AnnotatorRedactionListItem>
      </li>
    </ul>
  </div>
</template>

<script lang="ts">
  import type { FeatureCollection } from 'geojson';
  import AnnotatorRedactionListItem from 'src/components/AnnotatorRedactionListItem.vue';
  import { defineComponent, PropType } from 'vue';

  export default defineComponent({
    name: 'AnnotatorRedactionList',
    components: { AnnotatorRedactionListItem },
    props: {
      geojson: {
        type: Object as PropType<FeatureCollection>,
        required: true,
      },
    },
    data() {
      return {};
    },
  });
</script>
