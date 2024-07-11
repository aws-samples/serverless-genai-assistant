<script setup>
/* Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0 */
</script>

<template>
    <div class="logo">
      <!-- <img src="path/to/logo.png" alt="Logo"> -->
    </div>
      <span class="session-login-info"> <slot/></span>
</template>

<style scoped>

.logo {
  width: 10vw;
}
.logo img {
  height: 40px;
}

.session-login-info {
  margin-right: 0.5vw;
  align-content: center;
}

.session-info a {
  color: #58d82e;
  text-decoration: none;
}

</style>