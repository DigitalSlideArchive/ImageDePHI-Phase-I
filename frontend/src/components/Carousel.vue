<template>
  <div id="carousel" class="overflow-scroll">
    <div v-for="url in imageUrls" :key="url" class="slide">
      <img :src="url" class="img-thumbnail" />
    </div>
  </div>
</template>

<script lang="ts">
  import { defineComponent } from 'vue';

  import { getAssociatedLabels } from '../api/item';

  export default defineComponent({
    name: 'Carousel',
    props: {
      itemId: { type: String, required: true },
      size: { type: Number, required: false, default: 75 },
    },
    emits: [],
    data() {
      return {
        imageUrls: [
          `/api/v1/item/${this.itemId}/tiles/thumbnail?width=${this.size}&height=${this.size}`,
        ],
      };
    },
    computed: {
      cssVars() {
        return {
          '--size': `${this.size}px`,
        };
      },
    },
    async mounted() {
      const imageLabels = await getAssociatedLabels(this.itemId);
      imageLabels.forEach((label) => {
        this.imageUrls.push(
          `/api/v1/item/${this.itemId}/tiles/images/${label}?width=${this.size}&height=${this.size}`,
        );
      });
    },
    methods: {},
  });
</script>

<style>
  #carousel {
    overflow-y: hidden;
    overflow-x: auto;
    white-space: nowrap;
  }

  #carousel .slide {
    width: var(--size);
    height: var(--size);
    display: inline-block;
  }
</style>
