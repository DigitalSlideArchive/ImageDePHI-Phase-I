<template>
  <div>
    <AnnotatorMap v-model:geojson="geojson" :item-id="itemId"> </AnnotatorMap>
  </div>
</template>

<script lang="ts">
  import type { FeatureCollection } from 'geojson';
  import AnnotatorMap from 'src/components/AnnotatorMap.vue';
  import { defineComponent } from 'vue';

  export default defineComponent({
    name: 'Annotator',
    components: { AnnotatorMap },
    props: {
      itemId: { type: String, required: true },
    },
    data() {
      return {
        geojson: {} as FeatureCollection,
      };
    },
  });
</script>
