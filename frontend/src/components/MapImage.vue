<script lang="ts">
  import { ref } from 'vue';
  import geo from 'geojs';

  export default {
    components: {},
    props: {
      itemId: {
        type: String,
        required: true,
      },
    },
    setup(props) {
      return {
        map: geo.map,
        annotationLayer: geo.annotationLayer,
        isEditting: false,
        isCreating: false,
        currentlyEdittingIndex: 0,
      };
    },
  };
</script>
