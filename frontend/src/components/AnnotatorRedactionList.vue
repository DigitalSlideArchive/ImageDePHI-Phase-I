<template>
  <ul class="list-group">
    <li
      v-for="feature in features"
      :key="feature.properties.annotationId"
      class="list-group-item p-0"
    >
      <AnnotatorRedactionListItem
        :name="feature.properties.name"
        :description="feature.properties.description"
        :is-editting="isEditting"
        :is-creating="isCreating"
        :currently-editting-index="currentlyEdittingIndex"
        :annotation-id="feature.properties.annotationId"
        @update-name="$emit('updateName', $event)"
        @update-description="$emit('updateDescription', $event)"
        @begin-edit="$emit('beginEdit', $event)"
        @end-edit="$emit('endEdit', $event)"
        @delete-feature="$emit('deleteFeature', $event)"
      >
        >
      </AnnotatorRedactionListItem>
    </li>
    <button
      :readonly="isEditting || isCreating"
      :disabled="isEditting || isCreating"
      type="button"
      class="list-group-item list-group-item-action bg-{{(isEditting || isCreating) ? 'primary' : 'blue-100' }} text-black text-center"
      @click="$emit('createAnnotation')"
    >
      {{
        isEditting || isCreating
          ? 'Waiting to finish drawing...'
          : 'Create new annotation'
      }}
    </button>
    <button
      v-if="!isEditting && !isCreating"
      type="button"
      class="btn btn-primary"
      @click="$emit('downloadRedacted')"
    >
      Download redacted image
    </button>
  </ul>
</template>

<script lang="ts">
  import AnnotatorRedactionListItem from './AnnotatorRedactionListItem.vue';
  import type { GeoJSON } from '../types';
  import { defineComponent, PropType } from 'vue';

  export default defineComponent({
    name: 'AnnotatorRedactionList',
    components: { AnnotatorRedactionListItem },
    props: {
      features: {
        type: Object as PropType<Array<GeoJSON.Feature>>,
        required: true,
      },
      isEditting: {
        type: Boolean,
        required: true,
      },
      isCreating: {
        type: Boolean,
        required: true,
      },
      currentlyEdittingIndex: {
        type: Number,
        required: true,
      },
    },
    emits: [
      'createAnnotation',
      'updateName',
      'updateDescription',
      'beginEdit',
      'endEdit',
      'deleteFeature',
      'downloadRedacted',
    ],
    methods: {},
  });
</script>
