<template>
  <div class="row">
    <div class="col">
      <div class="card">
        <div class="card-body">
          <div class="row">
            <div class="col"><div id="map" style="height: 800px"></div></div>
            <div class="col border-start">
              <AnnotatorRedactionList
                :features="geojson.features"
                :is-editting="isEditting"
                :is-creating="isCreating"
                :currently-editting-index="currentlyEdittingIndex"
                @update-name="handleFeatureNameUpdate"
                @update-description="handleFeatureDescriptionUpdate"
                @begin-edit="handleBeginEdit"
                @end-edit="handleEndEdit"
                @create-annotation="handleNewAnnotation"
                @delete-feature="handleDeleteFeature"
              ></AnnotatorRedactionList>
            </div>
          </div>
          <div class="row border-top">
            <Carousel :item-id="itemId"></Carousel>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script lang="ts">
  import geo from 'geojs';
  import { defineComponent, PropType } from 'vue';

  import api from '../api';
  import { GeoJSON, TileMetadata } from '../types';
  import AnnotatorRedactionList from './AnnotatorRedactionList.vue';
  import Carousel from './Carousel.vue';

  export default defineComponent({
    name: 'AnnotatorMap',
    components: { AnnotatorRedactionList, Carousel },
    props: {
      itemId: {
        type: String,
        required: true,
      },
      tileMetadata: {
        type: Object as PropType<TileMetadata>,
        required: true,
      },
      geojson: {
        type: Object as PropType<GeoJSON>,
        required: true,
      },
    },
    emits: ['update:geojson'],
    data() {
      return {
        map: geo.map,
        annotationLayer: geo.annotationLayer,
        isEditting: false,
        isCreating: false,
        currentlyEdittingIndex: 0,
      };
    },
    mounted() {
      const pixelParams = geo.util.pixelCoordinateParams(
        '#map',
        this.tileMetadata.sizeX,
        this.tileMetadata.sizeY,
        this.tileMetadata.tileWidth,
        this.tileMetadata.tileHeight,
      );
      this.map = geo.map({
        ...pixelParams.map,
        clampZoom: true,
      });
      this.map.createLayer('osm', {
        ...pixelParams.layer,
        url: (x: number, y: number, z: number): string =>
          `${api.tileMetadata(this.itemId).route}/zxy/${z}/${x}/${y}`,
        autoResize: true,
      });
      this.annotationLayer = this.map.createLayer('annotation', {
        annotations: ['polygon'],
      });
      this.annotationLayer.geojson(this.geojson, true);
      this.annotationLayer.geoOn(
        geo.event.annotation.mode,
        this.emitGeoJSONonNew,
      );
    },
    methods: {
      emitGeoJSONonNew(status) {
        if (
          status.mode === null &&
          (status.oldMode === 'polygon' || status.oldMode === 'edit')
        ) {
          this.$emit('update:geojson', this.annotationLayer.geojson());
          this.isEditting = false;
          this.isCreating = false;
        }
      },
      handleFeatureNameUpdate(event) {
        const annotation = this.annotationLayer.annotationById(event.id);
        annotation.name(event.name);
        annotation.modified();
        this.annotationLayer.draw();
        this.$emit('update:geojson', this.annotationLayer.geojson());
      },
      handleFeatureDescriptionUpdate(event) {
        this.annotationLayer
          .annotationById(event.id)
          .description(event.description);
        const geojson = this.annotationLayer.geojson();
        geojson.features.find(
          (element) => element.properties.annotationId === event.id,
        ).properties.description = event.description;
        this.$emit('update:geojson', geojson);
      },
      handleBeginEdit(event) {
        const annotation = this.annotationLayer.annotationById(event);
        this.annotationLayer.mode('edit', annotation);
        annotation.state('edit');
        this.isEditting = true;
        this.isCreating = false;
        this.currentlyEdittingIndex = event;
        this.annotationLayer.draw();
      },
      handleEndEdit(event) {
        this.annotationLayer.mode('done');
        this.annotationLayer.mode(null);
        this.isEditting = false;
        this.isCreating = false;
        this.$emit('update:geojson', this.annotationLayer.geojson());
      },
      handleNewAnnotation(event) {
        this.annotationLayer.mode('polygon');
        this.isEditting = false;
        this.isCreating = true;
      },
      handleDeleteFeature(event) {
        const annotation = this.annotationLayer.annotationById(event);
        this.annotationLayer.removeAnnotation(annotation);
        this.annotationLayer.draw();
        this.annotationLayer.mode('done');
        this.annotationLayer.mode(null);
        this.isEditting = false;
        this.isCreating = false;
        this.$emit('update:geojson', this.annotationLayer.geojson());
      },
    },
  });
</script>
