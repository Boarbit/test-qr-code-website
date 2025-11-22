<script lang="ts">
  'use legacy';
  import { goto } from '$app/navigation';
  import QrScanner from '$lib/components/QrScanner.svelte';

  let navigating = false;

  async function handleDetect(event: CustomEvent<{ text: string }>) {
    if (navigating) {
      return;
    }

    const code = event.detail.text.trim();
    if (!code) {
      return;
    }

    navigating = true;
    await goto(`/scan/${encodeURIComponent(code)}`);
  }
</script>

<main class="scan-page">
  <h1>Scan a QR Code</h1>
  <p class="intro">
    Point your camera at any PAQS label to jump straight to the container details.
  </p>

  <QrScanner
    title="Live scanner"
    description="Start the camera, align the QR label in the frame, and we’ll redirect you once it’s detected."
    on:detect={handleDetect}
  >
    <svelte:fragment slot="tips">
      <ul>
        <li>Allow camera access when prompted.</li>
        <li>If multiple cameras are listed, pick the rear or high-resolution option.</li>
        <li>After detection we’ll open the matching <code>/scan/&lt;code&gt;</code> page automatically.</li>
      </ul>
    </svelte:fragment>
  </QrScanner>
</main>

<style>
  .scan-page {
    max-width: 860px;
    margin: 0 auto;
    padding: 32px 16px 64px;
    display: flex;
    flex-direction: column;
    gap: 20px;
  }

  h1 {
    text-align: center;
    font-size: 2.2rem;
    margin: 0;
  }

  .intro {
    text-align: center;
    color: var(--color-text-muted);
    margin: 0;
  }

  @media (max-width: 640px) {
    .scan-page {
      padding: 24px 12px 48px;
    }
  }
</style>
