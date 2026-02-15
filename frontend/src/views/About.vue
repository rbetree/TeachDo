<template>
  <PageLayout :hideSteps="true">
    <main class="about-main">
      <section class="about-content">
        <p class="about-label">About AI2PPT</p>
        <h1 class="about-title">
          Less Noise.<br />More Signal.
        </h1>
        <p class="about-body">
          We believe that presentation software has become too cluttered. Our goal is to strip away the non-essential and use advanced AI to focus purely on your narrative.
        </p>
        <p class="about-body">
          Designed for high-performance individuals who value clarity, precision, and aesthetics.
        </p>
      </section>
    </main>
  </PageLayout>
</template>

<script setup lang="ts">
import { PageLayout } from '@/components/common'
</script>

<style scoped lang="scss">
.about-main {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: calc(100vh - 160px);
}

.about-content {
  max-width: 600px;
  text-align: center;
}

.about-label {
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--text-secondary);
  margin-bottom: 1.5rem;
}

.about-title {
  font-size: 3rem;
  font-weight: 600;
  letter-spacing: -0.03em;
  margin-bottom: 1.5rem;
}

.about-body {
  font-size: 1rem;
  color: var(--text-secondary);
  line-height: 1.6;
  margin-bottom: 1.5rem;
}

@media (max-width: 768px) {
  .about-title {
    font-size: 2.2rem;
  }
}
</style>

