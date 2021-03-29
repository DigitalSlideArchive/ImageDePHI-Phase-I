<template>
  <div></div>
</template>

<script lang="ts">
  import geo from 'geojs';
  import type { FeatureCollection } from 'geojson';
  import { api } from 'src/api';
  import { defineComponent, PropType } from 'vue';

  export default defineComponent({
    name: 'AnnotatorMap',
    props: {
      itemId: { type: String, required: true },
      geojson: {
        type: Object as PropType<FeatureCollection>,
        required: false,
        default: undefined,
      },
    },
    emits: ['update:geojson'],
    data() {
      return {
        map: geo.map,
        annotationLayer: geo.annotationLayer,
      };
    },
    watch: {
      geojson(newGeoJSON: FeatureCollection) {
        this.annotationLayer.geojson(newGeoJSON, 'update');
      },
    },
    async mounted() {
      const tileMetadata = await api.tileMetadata(this.itemId).fetch();
      const pixelParams = geo.util.pixelCoordinateParams(
        this.$el,
        tileMetadata.sizeX,
        tileMetadata.sizeY,
        tileMetadata.tileWidth,
        tileMetadata.tileHeight,
      );
      this.map = geo.map({
        ...pixelParams.map,
        clampZoom: false,
      });
      this.map.createLayer('osm', {
        ...pixelParams.layer,
        url: (x: number, y: number, z: number): string =>
          `${api.tileMetadata(this.itemId).route}/zxy/${z}/${x}/${y}`,
      });
      this.annotationLayer = this.map.createLayer('annotation', {
        annotations: ['polygon'],
      });
      this.annotationLayer.geoOn(geo.event.annotation.state, this.emitGeoJSON);
      api
        .geojson(this.itemId)
        .fetch()
        .then((res) => this.emitGeoJSON(res));
    },
    methods: {
      emitGeoJSON(newGeoJSON?: FeatureCollection) {
        if (newGeoJSON !== undefined) {
          this.$emit('update:geojson', newGeoJSON);
        } else {
          this.$emit('update:geojson', this.annotationLayer.geojson());
        }
      },
    },
  });
</script>
