<template>
  <div v-if="geojson && tileMetadata">
    <AnnotatorMap
      v-model:geojson="geojson"
      :tile-metadata="tileMetadata"
      :item-id="itemId"
      :related-image-urls="relatedImageUrls"
    ></AnnotatorMap>
  </div>
</template>

<script lang="ts">
  import api from 'src/api';
  import AnnotatorMap from 'src/components/AnnotatorMap.vue';
  import type { GeoJSON, TileMetadata } from 'src/types';
  import { defineComponent } from 'vue';

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
      api
        .relatedImageURLs(this.itemId)
        .fetch()
        .then((r) => {
          this.relatedImageUrls = r.map(
            (image) =>
              `/api/v1/item/${this.itemId}/tiles/images/${image}?width=200&height=200`,
          );
        });
    },
  });
</script>
