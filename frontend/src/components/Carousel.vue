<template>
  <div id="carousel">
    <div v-for="url in imageUrls" :key="url" class="slide">
      <img :src="url" class="img-thumbnail" />
    </div>
  </div>
</template>

<script lang="ts">
  import { defineComponent } from 'vue';

  export default defineComponent({
    name: 'Carousel',
    props: { imageUrls: { type: Array, required: true, default: () => [] } },
    emits: [],
    methods: {},
  });
</script>

<style>
  #carousel {
    width: 100%;
    height: 200px;
    overflow: visible;
    white-space: nowrap;
  }

  #carousel .slide {
    display: inline-block;
  }
</style>
