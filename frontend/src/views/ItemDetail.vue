<template>
  <PageTitle :title="`Item #${itemId}`"></PageTitle>
  <div v-if="geojson && tileMetadata">
    <AnnotatorMap
      v-model:geojson="geojson"
      :tile-metadata="tileMetadata"
      :item-id="itemId"
    ></AnnotatorMap>
  </div>
</template>

<script lang="ts">
  import { defineComponent } from 'vue';

  import api from '../api';
  import AnnotatorMap from '../components/AnnotatorMap.vue';
  import type { GeoJSON, TileMetadata } from '../types';

  export default defineComponent({
    name: 'ItemDetail',
    components: { AnnotatorMap },
    props: {
      itemId: { type: String, required: true },
    },
    data() {
      return {
        geojson: undefined as GeoJSON | undefined,
        tileMetadata: undefined as TileMetadata | undefined,
        relatedImageUrls: undefined as Array<String> | undefined,
      };
    },
    watch: {
      geojson(newValue) {
        api.putgeojson(this.itemId).put({ imagedephi: { geojson: newValue } });
      },
    },
    mounted() {
      api
        .tileMetadata(this.itemId)
        .fetch()
        .then((r) => {
          this.tileMetadata = r;
        });
      api
        .geojson(this.itemId)
        .fetch()
        .then((r) => {
          if (r?.imagedephi?.geojson) {
            this.geojson = r.imagedephi.geojson;
          } else {
            this.geojson = {
              type: 'FeatureCollection',
              features: [],
            };
          }
        });
    },
  });
</script>
