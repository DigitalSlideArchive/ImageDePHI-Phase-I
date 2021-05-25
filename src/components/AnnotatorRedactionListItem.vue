<template>
  <div
    id="confirmModal"
    class="modal fade"
    tabindex="-1"
    aria-labelledby="exampleModalLabel"
    aria-hidden="true"
  >
    <div class="modal-dialog">
      <div class="modal-content">
        <div class="modal-header">
          <h5 id="exampleModalLabel" class="modal-title">Are you sure?</h5>
          <button
            type="button"
            class="btn-close"
            data-bs-dismiss="modal"
            aria-label="Close"
          ></button>
        </div>
        <div class="modal-body">Deleting is permanent.</div>
        <div class="modal-footer">
          <button
            id="deleteButton"
            type="button"
            class="btn btn-danger"
            data-bs-dismiss="modal"
            @click.stop="
              if ($event?.target?.id == 'deleteButton') {
                $emit('deleteFeature', annotationId);
              }
            "
          >
            Delete
          </button>
        </div>
      </div>
    </div>
  </div>

  <div class="row text-center">
    <div class="input-group">
      <button
        :disabled="!localEdit"
        class="btn btn-sm btn-danger -text border-start"
        type="button"
        data-bs-toggle="modal"
        data-bs-target="#confirmModal"
      >
        <i class="bi-trash"></i>
      </button>
      <input
        :value="name"
        :readonly="!localEdit"
        type="text"
        class="form-control form-control-plaintext border-0 focus pl-2 p-2"
        @input="
          $emit('updateName', {
            id: annotationId,
            name: $event.target.value,
          })
        "
      />
      <select
        :value="description"
        class="form-select border-0 border-start"
        :disabled="!localEdit"
        @input="
          $emit('updateDescription', {
            id: annotationId,
            description: $event.target.value,
          })
        "
      >
        <option selected value="other">other</option>
        <option
          v-for="redactionType in redactionTypes"
          :key="redactionType"
          :value="redactionType"
        >
          {{ redactionType }}
        </option>
      </select>
      <button
        :class="`btn btn-primary btn-sm btn-block btn-${
          localEdit ? 'success' : 'warning'
        } input-group-text border-start`"
        type="button"
        :disabled="isEditting && currentlyEdittingIndex !== annotationId"
        @click.stop="
          {
            if (isEditting && currentlyEdittingIndex === annotationId) {
              $emit('endEdit', annotationId);
            } else {
              $emit('beginEdit', annotationId);
            }
          }
        "
      >
        <i
          :class="
            isEditting && currentlyEdittingIndex === annotationId
              ? 'bi-check2'
              : 'bi-pencil'
          "
        ></i>
      </button>
    </div>
  </div>
</template>

<script lang="ts">
  import { defineComponent } from 'vue';

  export default defineComponent({
    name: 'AnnotatorRedactionListItem',
    props: {
      name: {
        type: String,
        required: true,
      },
      description: {
        type: String,
        required: false,
        default: 'other',
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
      annotationId: {
        type: Number,
        required: true,
      },
    },
    emits: [
      'beginEdit',
      'endEdit',
      'updateName',
      'updateDescription',
      'deleteFeature',
    ],
    data() {
      return {
        redactionTypes: [
          'patient name',
          'date of birth',
          'social security number',
          'demographics',
          'facility/physician information',
        ],
        editing: false,
      };
    },
    computed: {
      localEdit() {
        return (
          this.isEditting && this.currentlyEdittingIndex === this.annotationId
        );
      },
    },
    methods: {
      handleClick(event) {
        console.log(event);

        if (this.currentlyEdittingIndex === this.annotationId) {
          this.$emit('endEdit', this.annotationId);
        } else {
          this.$emit('beginEdit', this.annotationId);
        }
      },
    },
  });
</script>
