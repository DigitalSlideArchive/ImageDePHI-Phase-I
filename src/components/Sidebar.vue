<template>
  <nav
    id="sidebarMenu"
    class="col-md-3 col-lg-2 d-md-block bg-light sidebar collapse"
  >
    <div class="position-sticky pt-3">
      <ul class="nav flex-column">
        <li class="nav-item">
          <router-link class="nav-link" to="/"
            ><i class="bi bi-house-door"></i> Home</router-link
          >
          <router-link class="nav-link" to="/login"
            ><i class="bi bi-key"></i> Login</router-link
          >
          <router-link class="nav-link" to="/5fa5809c4117741d21eb08e9"
            ><i class="bi bi-gear"></i> Sample Annotator</router-link
          >
        </li>
      </ul>
      <h6
        class="sidebar-heading d-flex justify-content-between align-items-center px-3 mt-4 mb-1 text-muted"
      >
        <span>Saved reports</span>
        <a class="link-secondary" href="#" aria-label="Add a new report"
          ><i class="bi bi-plus-circle"></i>
        </a>
      </h6>
      <ul class="nav flex-column mb-2"></ul>
    </div>
  </nav>
</template>

<script lang="ts">
  import { defineComponent } from 'vue';

  export default defineComponent({
    name: 'Sidebar',
    props: {},
    emits: [],
    methods: {},
  });
</script>
