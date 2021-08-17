<script setup lang="ts">
  import { watch } from 'fs';
  import geo from 'geojs';
  import { ref, onMounted, toRefs } from 'vue';
  import { useAuthentication } from '../composables/useAuthentication';

  const { token, user, authenticate, api } = useAuthentication();

  const username = ref('');
  const password = ref('');
  const login = async () => {
    authenticate(username.value, password.value);
  };

  const itemid = ref('');

  const ifds = ref([]);
  const getIfds = async () => {
    const resp = await api(
      `/api/v1/item/${itemid.value}/imagedephi/destructure`,
    );
    ifds.value = await resp.json();
  };

  const getMetadata = async () => {
    const resp = await api(`/api/v1/item/${itemid.value}/imagedephi/metadata`);
    const json = await resp.json();
    metadata.value = json;
    mountGeoJs();
  };

  const mountGeoJs = async () => {
    const resp = await api(`/api/v1/item/${itemid.value}/imagedephi/tile`);
    const json = await resp.json();
    const tileMetadata = json;
    const pixelParams = geo.util.pixelCoordinateParams(
      '#map',
      tileMetadata.sizeX,
      tileMetadata.sizeY,
      256,
      256,
    );
    const map = geo.map({
      ...pixelParams.map,
      clampZoom: true,
    });
    map.createLayer('osm', {
      ...pixelParams.layer,
      url: (x: number, y: number, z: number): string =>
        `http://localhost:8080/api/v1/item/${itemid.value}/imagedephi/tile/${z}/${x}/${y}?token=${token.value}`,
      autoResize: true,
    });
    geo.annotationLayer = map.createLayer('annotation', {
      annotations: ['polygon'],
    });
  };
</script>

<template>
  <nav class="navbar navbar-light bg-light mx-auto" v-if="!token">
    <form class="container-fluid">
      <div class="input-group">
        <input
          type="username"
          class="form-control"
          placeholder="Username"
          v-model="username"
        />
        <input
          type="password"
          class="form-control"
          placeholder="Password"
          v-model="password"
        />
        <button
          class="btn btn-outline-success me-2"
          v-on:click="login"
          type="button"
        >
          submit
        </button>
      </div>
    </form>
  </nav>
  <nav class="navbar navbar-light bg-light mx-auto" v-if="token">
    <form class="container-fluid">
      <div class="input-group">
        <input
          type="text"
          class="form-control"
          placeholder="#ItemID"
          v-model="itemid"
        />
        <button
          class="btn btn-outline-success me-2"
          type="button"
          v-on:click="mountGeoJs"
        >
          search
        </button>
      </div>
    </form>
  </nav>
  <div>
    <div id="map"></div>
  </div>
</template>

<style>
  #map {
    width: 100%;
    height: 100%;
    padding: 0;
    margin: 0;
  }
</style>
