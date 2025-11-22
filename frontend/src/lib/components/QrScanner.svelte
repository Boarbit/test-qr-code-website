<script lang="ts">
  'use legacy';
  import { browser } from '$app/environment';
  import { BrowserMultiFormatReader, type IScannerControls } from '@zxing/browser';
  import { NotFoundException } from '@zxing/library';
  import { createEventDispatcher, onDestroy } from 'svelte';

  type DetectEvent = {
    text: string;
  };

  const dispatch = createEventDispatcher<{ detect: DetectEvent }>();

  export let title = 'Scan a QR Code';
  export let description = '';
  export let startLabel = 'Start scanning';
  export let stopLabel = 'Stop';
  export let mirror = true;
  export let autoStopOnDetect = true;
  export let enabled = true;

  let videoEl: HTMLVideoElement | null = null;
  let reader: BrowserMultiFormatReader | null = null;
  let controls: IScannerControls | null = null;
  let startPromise: Promise<IScannerControls> | null = null;

  let devices: MediaDeviceInfo[] = [];
  let selectedDeviceId: string | null = null;

  let sessionSeq = 0;
  let activeToken = 0;

  let scanning = false;
  let error = '';
  let statusMessage = '';
  let permissionPromptNeeded = false;

  function resetReader() {
    if (!reader) {
      return;
    }

    const maybeReset = (reader as { reset?: () => void }).reset;
    if (typeof maybeReset === 'function') {
      try {
        maybeReset.call(reader);
      } catch {
        // noop
      }
      return;
    }

    const maybeStopStreams = (reader as { stopStreams?: () => void }).stopStreams;
    if (typeof maybeStopStreams === 'function') {
      try {
        maybeStopStreams.call(reader);
      } catch {
        // noop
      }
    }
  }

  async function ensureDevices() {
    if (!browser) {
      return;
    }

    if (!navigator.mediaDevices?.getUserMedia) {
      error = 'Camera access is not supported in this browser.';
      throw new Error('unsupported');
    }

    if (devices.length > 0) {
      return;
    }

    try {
      // Request access once so labels are available when selecting devices.
      const permissionStream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: 'environment' }
      });
      permissionPromptNeeded = false;
      permissionStream.getTracks().forEach((track) => track.stop());

      const allDevices = await navigator.mediaDevices.enumerateDevices();
      devices = allDevices.filter((device) => device.kind === 'videoinput');

      if (!devices.length) {
        error = 'No camera devices were found. Connect a camera and try again.';
        throw new Error('no-devices');
      }

      const preferred = devices.find((device) => /back|rear|environment/i.test(device.label));
      selectedDeviceId = (preferred ?? devices[0]).deviceId;
    } catch (err) {
      permissionPromptNeeded = true;
      if (err instanceof Error) {
        if (err.name === 'NotAllowedError') {
          error = 'Camera permission denied. Allow access in your browser to scan QR codes.';
        } else if (err.name === 'NotFoundError') {
          error = 'No camera detected. Attach a camera or use a device with one built in.';
        } else {
          error = `Unable to access the camera: ${err.message}`;
        }
      } else {
        error = 'Unable to access the camera.';
      }
      throw err;
    }
  }

  async function startScanning() {
    if (scanning || !enabled) {
      return;
    }

    error = '';
    statusMessage = '';

    const token = ++sessionSeq;
    activeToken = token;
    scanning = true;

    try {
      await ensureDevices();
    } catch {
      if (activeToken === token) {
        scanning = false;
      }
      return;
    }

    if (activeToken !== token) {
      return;
    }

    if (!videoEl) {
      if (activeToken === token) {
        scanning = false;
      }
      error = 'Video element is not ready yet.';
      return;
    }

    if (!reader) {
      reader = new BrowserMultiFormatReader();
    } else {
      resetReader();
    }

    const promise = reader.decodeFromVideoDevice(
      selectedDeviceId ?? undefined,
      videoEl,
      (result, scanError, ctrl) => {
        if (activeToken !== token || !scanning) {
          return;
        }

        if (result) {
          const text = result.getText().trim();
          if (text) {
            statusMessage = `QR detected: ${text}`;
            dispatch('detect', { text });
            if (autoStopOnDetect) {
              ctrl.stop();
              resetReader();
              controls = null;
              scanning = false;
              activeToken += 1;
            }
          }
        }

        if (scanError && !(scanError instanceof NotFoundException)) {
          error = 'Scanning error. Adjust the QR code and try again.';
        }
      }
    );

    startPromise = promise;

    try {
      const ctrl = await promise;
      if (activeToken === token && scanning) {
        controls = ctrl;
      } else {
        try {
          ctrl.stop();
        } catch {
          // ignore stop issues for stale sessions
        }
      }
    } catch (err) {
      const stillActive = activeToken === token;
      if (stillActive) {
        scanning = false;
        resetReader();
        controls = null;
        if (err instanceof Error) {
          error = err.message;
        } else {
          error = 'Failed to start the QR scanner.';
        }
      }
    } finally {
      if (startPromise === promise) {
        startPromise = null;
      }
      if (activeToken !== token) {
        resetReader();
      }
    }
  }

  function stopScanning() {
    activeToken += 1;

    const pending = startPromise;
    if (pending) {
      pending
        .then((ctrl) => {
          try {
            ctrl.stop();
          } catch {
            // ignore stop errors on cancelled streams
          }
        })
        .catch(() => {
          // suppress errors for aborted start attempts
        });
      startPromise = null;
    }

    if (controls) {
      try {
        controls.stop();
      } catch {
        // ignore stop errors on active streams
      }
      controls = null;
    }

    resetReader();
    scanning = false;
    statusMessage = '';
  }

  function handleDeviceChange(event: Event) {
    selectedDeviceId = (event.currentTarget as HTMLSelectElement).value;
    if (scanning) {
      stopScanning();
      void startScanning();
    }
  }

  onDestroy(() => {
    stopScanning();
  });
</script>

<section class="qr-scanner">
  <div class="scan-header">
    <h3>{title}</h3>
    {#if description}
      <p class="muted">{description}</p>
    {/if}
  </div>

  {#if error}
    <p class="message error">{error}</p>
  {/if}

  {#if statusMessage}
    <p class="message status">{statusMessage}</p>
  {/if}

  <div class="controls">
    <label>
      Camera source
      <select
        bind:value={selectedDeviceId}
        disabled={!devices.length || scanning}
        on:change={handleDeviceChange}
      >
        {#if !devices.length}
          <option value="">No cameras detected</option>
        {:else}
          {#each devices as device, index}
            <option value={device.deviceId}>{device.label || `Camera ${index + 1}`}</option>
          {/each}
        {/if}
      </select>
    </label>

    <div class="buttons">
      <button type="button" class="primary" on:click={startScanning} disabled={scanning || !enabled}>
        {scanning ? 'Scanning…' : startLabel}
      </button>
      <button type="button" on:click={stopScanning} disabled={!scanning}>
        {stopLabel}
      </button>
    </div>
  </div>

  <div class="video-wrapper">
    <video
      bind:this={videoEl}
      autoplay
      muted
      playsinline
      class:inactive={!scanning}
      class:mirror={mirror}
    ></video>
  </div>

  {#if permissionPromptNeeded}
    <p class="message warning">
      Grant camera permission in the browser prompt, then click “{startLabel}” again.
    </p>
  {/if}

  <div class="tips">
    <slot name="tips">
      <ul>
        <li>Hold the QR code steady and ensure it fills most of the preview.</li>
        <li>Improve focus by moving the code slowly toward or away from the lens.</li>
        <li>Once detected, the code appears above and any linked actions will run.</li>
      </ul>
    </slot>
  </div>
</section>

<style>
  .qr-scanner {
    background: var(--color-card-tertiary, rgba(255, 255, 255, 0.08));
    border: 1px solid var(--color-border, rgba(0, 0, 0, 0.08));
    border-radius: 16px;
    padding: 20px;
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  .scan-header h3 {
    margin: 0;
    font-size: 1.4rem;
  }

  .scan-header .muted {
    margin: 6px 0 0;
    color: var(--color-text-muted);
    font-size: 0.95rem;
  }

  .controls {
    display: flex;
    flex-wrap: wrap;
    gap: 16px;
    align-items: flex-end;
    justify-content: space-between;
  }

  label {
    display: flex;
    flex-direction: column;
    gap: 6px;
    font-weight: 600;
    min-width: 200px;
  }

  select {
    padding: 8px 10px;
    border-radius: 8px;
    border: 1px solid var(--color-border);
    background: var(--color-card, rgba(255, 255, 255, 0.05));
    color: inherit;
  }

  .buttons {
    display: flex;
    gap: 12px;
  }

  button {
    border: none;
    border-radius: 999px;
    padding: 10px 18px;
    font-weight: 600;
    cursor: pointer;
    background: var(--color-card-alt, rgba(0, 0, 0, 0.06));
    color: inherit;
    transition: transform 0.15s;
  }

  button.primary {
    background: var(--color-primary, #2f7a72);
    color: var(--color-text-on-primary, #ffffff);
  }

  button:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }

  button:not(:disabled):hover {
    transform: translateY(-1px);
  }

  .video-wrapper {
    position: relative;
    background: #000;
    border-radius: 16px;
    overflow: hidden;
    border: 1px solid var(--color-border);
    min-height: 280px;
    display: flex;
    justify-content: center;
    align-items: center;
    box-shadow: var(--shadow-card, 0 12px 24px rgba(0, 0, 0, 0.12));
  }

  video {
    width: 100%;
    height: auto;
    object-fit: cover;
  }

  video.mirror {
    transform: scaleX(-1);
  }

  video.inactive {
    opacity: 0.2;
  }

  .message {
    text-align: center;
    padding: 12px 16px;
    border-radius: 10px;
    margin: 0;
    font-weight: 500;
  }

  .message.error {
    background: rgba(229, 57, 53, 0.12);
    color: var(--color-danger, #d32f2f);
  }

  .message.warning {
    background: rgba(255, 193, 7, 0.16);
    color: var(--color-warning, #f57c00);
  }

  .message.status {
    background: rgba(76, 175, 80, 0.16);
    color: var(--color-success, #2e7d32);
  }

  .tips ul {
    list-style: disc;
    padding-left: 20px;
    margin: 0;
    display: flex;
    flex-direction: column;
    gap: 6px;
    color: var(--color-text-muted);
    font-size: 0.95rem;
  }

  @media (max-width: 640px) {
    .qr-scanner {
      padding: 16px;
    }

    .controls {
      flex-direction: column;
      align-items: stretch;
    }

    .buttons {
      justify-content: center;
    }
  }
</style>
