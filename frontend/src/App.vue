<template>
  <Header title="ImageDePHI"></Header>
  <div class="container-fluid">
    <div class="row">
      <Sidebar></Sidebar>
      <main class="col-md-9 ms-sm-auto col-lg-10 px-md-4">
        <router-view></router-view>
      </main>
    </div>
  </div>
</template>

<script lang="ts">
  import Header from './components/Header.vue';
  import PageTitle from './components/PageTitle.vue';
  import Sidebar from './components/Sidebar.vue';
  import { defineComponent } from 'vue';

  export default defineComponent({
    name: 'App',
    components: { Header, Sidebar, PageTitle },
  });
</script>

<style>
  main {
    width: 100%;
  }
</style>
