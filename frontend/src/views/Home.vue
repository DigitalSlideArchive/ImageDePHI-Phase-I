<template>
  <div><Carousel item-id="60d6f0e194e55ac87969c198"></Carousel></div>
</template>

<script lang="ts">
  import { defineComponent } from 'vue';
  import Carousel from '../components/Carousel.vue';

  export default defineComponent({
    name: 'Home',
    components: { Carousel },
  });
</script>

<style>
  #carousel {
    overflow-x: auto;
    white-space: nowrap;
  }

  #carousel .slide {
    width: var(--size);
    height: var(--size);
    display: inline-block;
  }
</style>
