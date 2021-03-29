<template>
  <div>
    <Annotator v-model:itemId="itemId" v-model:geojson="geojson"> </Annotator>
  </div>
</template>

<script lang="ts">
  import Annotator from 'src/components/Annotator.vue';
  import { defineComponent } from 'vue';

  export default defineComponent({
    name: 'App',
    components: { Annotator },
    data() {
      return {
        itemId: '5fa5809c4117741d21eb08e9',
        geojson: undefined,
      };
    },
  });
</script>
