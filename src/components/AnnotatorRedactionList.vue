<template>
  <ul class="list-group">
    <li
      v-for="feature in features"
      :key="feature.properties.annotationId"
      class="list-group-item p-0"
      @mouseover="
        $emit('beginHoveringOverFeature', feature.properties.annotationId)
      "
      @mouseleave="
        $emit('endHoveringOverFeature', feature.properties.annotationId)
      "
    >
      <AnnotatorRedactionListItem
        :name="feature.properties.name"
        :description="feature.properties.description"
        :is-editing="isEditing === feature.properties.annotationId"
        @update-name="
          $emit('updateFeatureName', {
            id: feature.properties.annotationId,
            name: $event,
          })
        "
        @update-description="
          $emit('updateFeatureDescription', {
            id: feature.properties.annotationId,
            description: $event,
          })
        "
        @begin-editing="
          $emit('beginFeatureEditing', feature.properties.annotationId)
        "
        @end-editing="
          $emit('endFeatureEditing', feature.properties.annotationId)
        "
      >
      </AnnotatorRedactionListItem>
    </li>
    <button
      :disabled="!!isEditing"
      type="button"
      class="list-group-item list-group-item-action text-center"
      @click="handleClick"
    >
      Create new annotation
    </button>
  </ul>
</template>

<script lang="ts">
  import AnnotatorRedactionListItem from 'src/components/AnnotatorRedactionListItem.vue';
  import { GeoJSON } from 'src/types';
  import { defineComponent, PropType } from 'vue';

  export default defineComponent({
    name: 'AnnotatorRedactionList',
    components: { AnnotatorRedactionListItem },
    props: {
      features: {
        type: Object as PropType<Array<GeoJSON.Feature>>,
        required: true,
      },
      isEditing: {
        type: Boolean as PropType<Number | Boolean>,
        required: true,
      },
    },
    emits: [
      'beginFeatureEditing',
      'endFeatureEditing',
      'updateFeatureName',
      'updateFeatureDescription',
      'createAnnotation',
      'beginHoveringOverFeature',
      'endHoveringOverFeature',
    ],
    methods: {
      handleClick(event) {
        this.$emit('createAnnotation');
      },
    },
  });
</script>
