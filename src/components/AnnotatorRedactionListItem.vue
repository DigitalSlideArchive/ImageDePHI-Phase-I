<template>
  <div class="row text-center">
    <div class="input-group">
      <input
        :value="name"
        :readonly="!isEditing"
        type="text"
        class="form-control form-control-plaintext border-0 focus"
        @input="$emit('updateName', $event.target.value)"
      />
      <select
        :value="description"
        class="form-select border-0 border-start"
        :disabled="!isEditing"
        @input="$emit('updateDescription', $event.target.value)"
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
        :class="`btn btn-sm btn-outline-${
          isEditing ? 'success' : 'warning'
        } input-group-text border-0 border-start`"
        type="button"
        @click.stop="handleClick"
      >
        <i :class="isEditing ? 'bi-check2' : 'bi-pencil'"></i>
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
      isEditing: {
        type: Boolean,
        required: true,
      },
    },
    emits: ['beginEditing', 'endEditing', 'updateName', 'updateDescription'],
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
    methods: {
      handleClick(event) {
        if (this.isEditing) {
          this.$emit('endEditing');
        } else {
          this.$emit('beginEditing');
        }
      },
    },
  });
</script>
