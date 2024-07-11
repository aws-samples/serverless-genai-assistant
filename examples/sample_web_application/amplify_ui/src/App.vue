<script setup>
/* Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0 */
import {Authenticator} from "@aws-amplify/ui-vue";
import "@aws-amplify/ui-vue/styles.css";
import MenuBar from "@/components/MenuBar.vue";
import AssistantConfig from "./components/AssistantConfig.vue"
import ChatComponent from "./components/ChatComponent.vue";
import {ref} from "vue";

const showLeftPane = ref(true);
const assistantConfigData = ref(null);

const toggleLeftPane = () => {
  showLeftPane.value = !showLeftPane.value;
};
</script>

<template>
  <authenticator hide-sign-up>
    <template v-slot="{ user, signOut }">
      <div class="container">
        <div class="menubar">
          <MenuBar>{{ user.signInDetails.loginId }} | <span @click="signOut" class="sign-out-link">Sign Out</span></MenuBar>
        </div>
        <div class="main_area">
          <div class="left-pane" :class="{ 'hidden': !showLeftPane }">
            <AssistantConfig ref="assistantConfigData"/>
          </div>
          <button @click="toggleLeftPane" class="toggle-btn" :class="{ 'hidden': !showLeftPane }">
            <span class="toggle-icon"></span>
          </button>
          <div class="right-pane">
            <chat-component :assistant-config="assistantConfigData"></chat-component>
          </div>
        </div>
      </div>
    </template>
  </authenticator>
</template>

<style scoped>
.container {
  display: flex;
  flex-direction: column;
  height: 100vh;
  width: 100vw;
}

.menubar {
  display: flex;
  height: 5vh;
  width: 100vw;
  background-color: #333;
  color: #fff;
  justify-content: space-between;
}

.main_area {
  display: flex;
  flex: 1;
  position: relative;
}

.left-pane {
  width: 25vw;
  margin-left: 0.1rem;
  min-width: 2vw;
  max-width: 40vw;
  height: calc(100vh - 5vh);
  overflow: auto;
  /*resize: horizontal;*/
  background-color: #f0f0f0;
  transition: width 0.3s ease-in-out, margin-left 0.3s ease-in-out;
}

.left-pane.hidden {
  width: 0;
  margin-left: 0;
  overflow: hidden;
}

.toggle-btn {
  position: absolute;
  left: 25vw;
  top: 50%;
  transform: translateY(-50%);
  z-index: 10;
  background-color: rgb(100, 103, 100);
  border: none;
  width: 24px;
  height: 48px;
  border-radius: 0 24px 24px 0;
  cursor: pointer;
  transition: left 0.3s ease-in-out, background-color 0.3s;
  display: flex;
  align-items: center;
  justify-content: center;
}

.toggle-btn:hover {
  background-color: #357abd;
}

.toggle-btn.hidden {
  left: 0;
  border-radius: 0 24px 24px 0;
}

.toggle-icon {
  width: 0;
  height: 0;
  border-top: 6px solid transparent;
  border-bottom: 6px solid transparent;
  border-right: 6px solid white;
  transition: transform 0.3s;
}

.toggle-btn.hidden .toggle-icon {
  transform: rotate(180deg);
}

.right-pane {
  display: flex;
  flex-grow: 1;
  justify-content: center;
}

.sign-out-link {
  color: #fff;
  cursor: pointer;
}

.sign-out-link:hover {
  color: #fff;
  background-color: #ff6b6b;
  padding: 5px 10px;
}
</style>