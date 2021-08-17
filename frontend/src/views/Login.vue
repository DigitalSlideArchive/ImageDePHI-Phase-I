<template>
  <PageTitle title="Login"></PageTitle>
  <div class="form-signin">
    <form @submit.prevent="onSubmit">
      <h1 class="h3 mb-3 fw-normal">Please sign in</h1>

      <div class="form-floating">
        <input
          id="floatingInput"
          v-model="username"
          type="username"
          class="form-control"
          placeholder="username"
        />
        <label for="floatingInput">User name</label>
      </div>
      <div class="form-floating">
        <input
          id="floatingPassword"
          v-model="password"
          type="password"
          class="form-control"
          placeholder="Password"
        />
        <label for="floatingPassword">Password</label>
      </div>

      <button class="w-100 btn btn-lg btn-primary" type="submit" @click="login">
        Sign in
      </button>
    </form>
  </div>
</template>

<script lang="ts">
  import { defineComponent } from 'vue';

  import PageTitle from '../components/PageTitle.vue';

  export default defineComponent({
    name: 'Login',
    components: { PageTitle },
    data() {
      return {
        username: '',
        password: '',
      };
    },
    methods: {
      async onSubmit() {
        const { username } = this;
        const { password } = this;
        await this.$store.dispatch('user/login', { username, password });
        this.$router.push('/');
      },
    },
  });
</script>

<style scoped>
  .form-signin {
    width: 100%;
    max-width: 330px;
    padding: 15px;
    margin: auto;
  }

  .form-signin .checkbox {
    font-weight: 400;
  }

  .form-signin .form-floating:focus-within {
    z-index: 2;
  }

  .form-signin input[type='username'] {
    margin-bottom: -1px;
    border-bottom-right-radius: 0;
    border-bottom-left-radius: 0;
  }

  .form-signin input[type='password'] {
    margin-bottom: 10px;
    border-top-left-radius: 0;
    border-top-right-radius: 0;
  }
</style>
