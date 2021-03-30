<template>
  <div v-if="geojson && tileMetadata" class="row">
    <AnnotatorMap
      v-model:geojson="geojson"
      :tile-metadata="tileMetadata"
      :item-id="itemId"
    ></AnnotatorMap>
  </div>
</template>

<script lang="ts">
  import api from 'src/api';
  import AnnotatorMap from 'src/components/AnnotatorMap.vue';
  import AnnotatorRedactionList from 'src/components/AnnotatorRedactionList.vue';
  import type { GeoJSON, TileMetadata } from 'src/types';
  import { defineComponent } from 'vue';

  export default defineComponent({
    name: 'ItemDetail',
    components: { AnnotatorMap, AnnotatorRedactionList },
    props: {
      itemId: { type: String, required: true },
    },
    data() {
      return {
        geojson: undefined as GeoJSON | undefined,
        tileMetadata: undefined as TileMetadata | undefined,
      };
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
          this.geojson = {
            type: 'FeatureCollection',
            features: [],
          };
        });
    },
  });
</script>
