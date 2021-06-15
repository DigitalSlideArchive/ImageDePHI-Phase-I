<template>
  <Header title="ImageDePHI"></Header>
  <div class="container-fluid">
    <div class="row">
      <Sidebar></Sidebar>
      <main class="col-md-9 ms-sm-auto col-lg-10 px-md-4">
        <PageTitle title="Item #5fa5809c4117741d21eb08e9"></PageTitle>
        <router-view></router-view>
      </main>
    </div>
  </div>
</template>

<script lang="ts">
  import Header from 'src/components/Header.vue';
  import PageTitle from 'src/components/PageTitle.vue';
  import Sidebar from 'src/components/Sidebar.vue';
  import { defineComponent } from 'vue';

  export default defineComponent({
    name: 'App',
    components: { Header, Sidebar, PageTitle },
  });
</script>
