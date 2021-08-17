<script setup lang="ts">
  import geo from 'geojs';
  import { ref } from 'vue';

  const props = defineProps<{
    itemId?: string;
  }>();
</script>

<template>
  <div id="map"></div>
</template>
