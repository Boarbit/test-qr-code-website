<script lang="ts">
  'use legacy';
  import { onDestroy, onMount } from 'svelte';
  import { get } from 'svelte/store';
  import { API_URL, MOCK_USER_HEADER, PERMISSIONS } from '$lib/config';
  import { activeUser, hasPermission } from '$lib/stores/mockUsers';
  import type { MockUser } from '$lib/stores/mockUsers';
  import { createSpeechRecognition, isSpeechRecognitionSupported } from '$lib/speech';
  import QrScanner from '$lib/components/QrScanner.svelte';

  type ItemExtraField = {
    id: number;
    label: string;
    value: string;
  };

  type ItemForm = {
    name: string;
    quantity: string;
    extras: ItemExtraField[];
  };

  type ItemDetailArray = Array<{ label: string; value: string }>;
  type ItemDetails = Record<string, string> | ItemDetailArray;

  type ContainerItemDto = {
    name: string;
    quantity: number;
    details?: ItemDetails;
  };

  type ContainerDto = {
    qr_code: string;
    name: string;
    contents: ContainerItemDto[];
  };

  const userStore = activeUser;

  type VoiceTarget =
    | { kind: 'containerName' }
    | { kind: 'itemName'; index: number }
    | { kind: 'itemQuantity'; index: number };

  const containerVoiceTarget: VoiceTarget = { kind: 'containerName' };
  const DETAIL_FIELD_OPTIONS = ['Condition', 'Volume', 'Size', 'Notes', 'Color', 'Value', 'Serial Number'] as const;
  const DETAIL_PLACEHOLDERS: Record<string, string> = {
    Condition: 'e.g. Mint',
    Volume: 'e.g. 2.5 L',
    Size: 'e.g. 12" x 8"',
    Notes: 'e.g. Handle with care',
    Color: 'e.g. Red',
    Value: 'e.g. $150',
    'Serial Number': 'e.g. SN1234'
  };

  let containerName = '';
  let newQrCode = '';
  let items: ItemForm[] = [createEmptyItem()];

  let createdContainer: ContainerDto | null = null;
  let saving = false;
  let error = '';
  let success = '';

  let activePersona: MockUser | null = null;
  let canCreate = false;
  let canDeleteContainer = false;

  let speechSupported = false;
  let speechSupportChecked = false;
  let speechRecognition: SpeechRecognition | null = null;
  let listening = false;
  let speechError = '';
  let activeVoiceTarget: VoiceTarget | null = null;
  let activeVoiceKey: string | null = null;
  let queuedVoiceTarget: VoiceTarget | null = null;
  let extraFieldId = 0;

  let deleteLoading = false;
  let deleteError = '';
  let deleteSuccess = '';

  $: activePersona = $activeUser ?? null;
  $: canCreate = hasPermission(activePersona, PERMISSIONS.create);
  $: canDeleteContainer = Boolean(
    hasPermission(activePersona, PERMISSIONS.update) || hasPermission(activePersona, PERMISSIONS.create)
  );

  onMount(() => {
    speechSupported = isSpeechRecognitionSupported();
    if (!speechSupported) {
      speechSupportChecked = true;
      return;
    }

    speechRecognition = createSpeechRecognition({ lang: 'en-US' });
    if (!speechRecognition) {
      speechSupported = false;
      speechSupportChecked = true;
      return;
    }

    speechRecognition.onstart = () => {
      console.log("onstart");
      listening = true;
      speechError = '';
    };

    speechRecognition.onresult = (event: SpeechRecognitionEvent) => {
      console.log("onresult");
      const result = event.results.item(event.results.length - 1);
      if (!result || !result.isFinal) {
        return;
      }

      const alternative = result.item(0);
      const transcript = alternative?.transcript.trim();
      if (!transcript) {
        return;
      }

      applyTranscript(transcript);
    };

    speechRecognition.onerror = (event: SpeechRecognitionErrorEvent) => {
      console.log("onerror");
      listening = false;
      queuedVoiceTarget = null;
      activeVoiceTarget = null;
      activeVoiceKey = null;
      speechError = errorMessageFor(event.error, event.message);
    };

    speechRecognition.onend = () => {
      console.log("onend");
      // listening = false;
      // const nextTarget = queuedVoiceTarget;
      // queuedVoiceTarget = null;
      activeVoiceKey = null;

      // if (nextTarget && speechRecognition) {
      //   startRecognition(nextTarget);
      //   return;
      // }

      activeVoiceTarget = null;
    };

    speechSupportChecked = true;
  });

  onDestroy(() => {
    speechRecognition?.abort();
    speechRecognition = null;
  });

  function voiceTargetKey(target: VoiceTarget): string {
    switch (target.kind) {
      case 'containerName':
        return 'container';
      case 'itemName':
        return `item-name-${target.index}`;
      case 'itemQuantity':
        return `item-quantity-${target.index}`;
    }
  }

  function targetIsListening(target: VoiceTarget) {
    return listening && activeVoiceKey === voiceTargetKey(target);
  }

  function toggleVoiceInput(target: VoiceTarget) {
    console.log("toggleVoiceInput");
    speechError = '';

    if (!speechRecognition || !speechSupported) {
      speechError = 'Voice input is not available in this browser.';
      return;
    }

    if (targetIsListening(target)) {
      console.log("targetIsListening(target)");
      queuedVoiceTarget = null;
      speechRecognition.abort();
      speech_all_off();
      return;
    }

    if (listening) {
      console.log("listening");
      queuedVoiceTarget = target;
      speechRecognition.abort();
      speech_all_off();
      listening = false;
      return;
    }
    console.log("startRecognition");
    startRecognition(target);
    speech_individual_switch(target, true);
  }

  function startRecognition(target: VoiceTarget) {
    if (!speechRecognition) {
      speechError = 'Voice input is not available in this browser.';
      return;
    }

    try {
      activeVoiceTarget = target;
      activeVoiceKey = voiceTargetKey(target);
      queuedVoiceTarget = null;
      speechRecognition.start();
    } catch (err) {
      listening = false;
      activeVoiceTarget = null;
      activeVoiceKey = null;
      speechError = err instanceof Error ? err.message : 'Unable to start voice input.';
    }
  }

  function errorMessageFor(errorCode: string | undefined, message: string | undefined) {
    switch (errorCode) {
      case 'not-allowed':
        return 'Microphone access was blocked. Allow access and try again.';
      case 'service-not-allowed':
        return 'Speech recognition service is unavailable for this browser or profile.';
      case 'network':
        return 'Speech service network error. Check your connection and retry.';
      case 'no-speech':
        return 'No speech detected. Try speaking again.';
      case 'aborted':
        return 'Voice capture was interrupted. Try again.';
      default:
        return message || errorCode || 'Voice input error.';
    }
  }

  const SMALL_NUMBER_WORDS: Record<string, number> = {
    zero: 0,
    one: 1,
    two: 2,
    three: 3,
    four: 4,
    five: 5,
    six: 6,
    seven: 7,
    eight: 8,
    nine: 9,
    ten: 10,
    eleven: 11,
    twelve: 12,
    thirteen: 13,
    fourteen: 14,
    fifteen: 15,
    sixteen: 16,
    seventeen: 17,
    eighteen: 18,
    nineteen: 19
  };

  const TENS_WORDS: Record<string, number> = {
    twenty: 20,
    thirty: 30,
    forty: 40,
    fifty: 50,
    sixty: 60,
    seventy: 70,
    eighty: 80,
    ninety: 90
  };

  const MAGNITUDE_WORDS: Record<string, number> = {
    hundred: 100,
    thousand: 1000
  };

  function parseQuantityText(raw: string): number | null {
    const trimmed = raw.trim();
    if (!trimmed) {
      return null;
    }

    const digitMatch = trimmed.match(/\d+/g);
    if (digitMatch?.length) {
      const numericString = digitMatch.join('');
      const parsed = Number.parseInt(numericString, 10);
      return Number.isFinite(parsed) ? parsed : null;
    }

    const tokens = trimmed
      .toLowerCase()
      .replace(/[^a-z\s-]/g, ' ')
      .split(/\s+/)
      .filter(Boolean);

    if (!tokens.length) {
      return null;
    }

    let total = 0;
    let current = 0;

    for (const token of tokens) {
      if (token === 'and') {
        continue;
      }

      if (token in SMALL_NUMBER_WORDS) {
        current += SMALL_NUMBER_WORDS[token];
        continue;
      }

      if (token in TENS_WORDS) {
        current += TENS_WORDS[token];
        continue;
      }

      if (token in MAGNITUDE_WORDS) {
        const magnitude = MAGNITUDE_WORDS[token];
        current = Math.max(current, 1) * magnitude;
        if (magnitude >= 1000) {
          total += current;
          current = 0;
        }
        continue;
      }

      return null;
    }

    const result = total + current;
    return Number.isFinite(result) ? result : null;
  }

  function quantityFromTranscript(transcript: string, currentValue: string) {
    const parsed = parseQuantityText(transcript);
    if (parsed !== null) {
      return `${parsed}`;
    }
    return currentValue ? `${currentValue} ${transcript}`.trim() : transcript;
  }

  function mergeTranscript(currentValue: string, transcript: string) {
    if (!currentValue) {
      return transcript;
    }
    return `${currentValue.trim()} ${transcript}`.trim();
  }

  function applyTranscript(transcript: string) {
    const target = activeVoiceTarget;
    if (!target) {
      return;
    }

    switch (target.kind) {
      case 'containerName': {
        containerName = mergeTranscript(containerName, transcript);
        break;
      }
      case 'itemName': {
        const currentItem = items[target.index];
        if (!currentItem) {
          return;
        }
        updateItemName(target.index, mergeTranscript(currentItem.name, transcript));
        break;
      }
      case 'itemQuantity': {
        const currentItem = items[target.index];
        if (!currentItem) {
          return;
        }
        updateItemQuantity(target.index, quantityFromTranscript(transcript, currentItem.quantity));
        break;
      }
    }
  }

  function authHeaders() {
    const user = get(userStore);
    if (!user) {
      throw new Error('Select a creator persona before saving.');
    }

    return {
      [MOCK_USER_HEADER]: user.id
    };
  }

  function sanitizedItems(): ContainerItemDto[] {
    return items
      .map((item) => {
        const trimmedName = item.name.trim();
        const parsedQuantity = parseQuantityText(item.quantity);
        const safeQuantity = parsedQuantity !== null && parsedQuantity >= 0 ? parsedQuantity : 0;

        const detailEntries = item.extras
          .map((extra) => {
            const label = (extra.label || DETAIL_FIELD_OPTIONS[0]).trim();
            const value = extra.value.trim();
            return [label, value] as [string, string];
          })
          .filter(([label, value]) => label && value);

        const details = detailEntries.length ? Object.fromEntries(detailEntries) : undefined;
        const hasAny = Boolean(trimmedName || safeQuantity > 0 || detailEntries.length);

        const sanitized: ContainerItemDto = {
          name: trimmedName,
          quantity: safeQuantity
        };

        if (details) {
          sanitized.details = details;
        }

        return { sanitized, hasAny };
      })
      .filter(({ hasAny }) => hasAny)
      .map(({ sanitized }) => sanitized);
  }

  function normalizedDetailEntries(details?: ItemDetails) {
    if (!details) {
      return [];
    }

    if (Array.isArray(details)) {
      return details
        .map(({ label, value }) => [label?.trim(), value?.trim()] as [string, string])
        .filter(([label, value]) => Boolean(label) && Boolean(value));
    }

    return Object.entries(details)
      .map(([label, value]) => [label.trim(), value?.trim() ?? ''])
      .filter(([label, value]) => Boolean(label) && Boolean(value));
  }

  function previewItemExtras(item: ContainerItemDto) {
    const extras: [string, string][] = [];

    for (const [key, value] of Object.entries(item)) {
      if (key === 'name' || key === 'quantity' || key === 'details') {
        continue;
      }
      const rendered = value == null ? '' : String(value);
      if (rendered.trim()) {
        extras.push([formatFieldLabel(key), rendered]);
      }
    }

    extras.push(...normalizedDetailEntries(item.details));

    return extras;
  }

  async function createContainer() {
    if (!canCreate) {
      error = 'You do not have permission to create containers.';
      success = '';
      return;
    }

    error = '';
    success = '';
    createdContainer = null;
    deleteError = '';
    deleteSuccess = '';

    const trimmedQr = newQrCode.trim();
    const trimmedName = containerName.trim();

    if (!trimmedQr) {
      error = 'Please provide a QR code before saving.';
      return;
    }

    if (!trimmedName) {
      error = 'Give this container a name (e.g. Red Drawer).';
      return;
    }

    const sanitized = sanitizedItems();
    if (sanitized.length === 0) {
      error = 'Add at least one item with a name or quantity.';
      return;
    }

    const payload = {
      qr_code: trimmedQr,
      name: trimmedName,
      contents: sanitized
    };

    saving = true;
    try {
      const headers = {
        'Content-Type': 'application/json',
        ...authHeaders()
      };
      const res = await fetch(`${API_URL}/containers`, {
        method: 'POST',
        headers,
        body: JSON.stringify(payload)
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || 'Failed to save container');
      }

      const data: ContainerDto = await res.json();
      const mergedContents =
        Array.isArray(data.contents) && data.contents.length
          ? data.contents.map((item, index) => {
              const fallback = sanitized[index];
              if (!item.details && fallback?.details) {
                return { ...item, details: fallback.details };
              }
              return item;
            })
          : sanitized;

      success = `Container ${data.name} saved successfully.`;
      createdContainer = { ...data, contents: mergedContents };
      containerName = '';
      newQrCode = '';
      items = [createEmptyItem()];
    } catch (err) {
      error = err instanceof Error ? err.message : 'Failed to save container';
    } finally {
      saving = false;
    }
  }

  async function deleteContainerByQr(qr: string) {
    if (!canDeleteContainer) {
      return;
    }

    const trimmed = qr.trim();
    if (!trimmed) {
      return;
    }

    deleteLoading = true;
    deleteError = '';
    deleteSuccess = '';

    try {
      const res = await fetch(`${API_URL}/containers/${encodeURIComponent(trimmed)}`, {
        method: 'DELETE',
        headers: authHeaders()
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || 'Failed to delete container');
      }

      deleteSuccess = `Container ${trimmed} deleted.`;
      createdContainer = null;
      success = '';
    } catch (err) {
      deleteError = err instanceof Error ? err.message : 'Failed to delete container';
    } finally {
      deleteLoading = false;
    }
  }

  function nextExtraFieldId() {
    extraFieldId += 1;
    return extraFieldId;
  }

  function createEmptyItem(): ItemForm {
    return { name: '', quantity: '', extras: [] };
  }

  function addItem() {
    if (!canCreate) {
      return;
    }
    items = [...items, createEmptyItem()];
  }

  function removeItem(index: number) {
    if (items.length === 1) {
      items = [createEmptyItem()];
      return;
    }
    items = items.filter((_, i) => i !== index);
  }

  function updateItemName(index: number, value: string) {
    items = items.map((item, i) => (i === index ? { ...item, name: value } : item));
  }

  function updateItemQuantity(index: number, value: string) {
    items = items.map((item, i) => (i === index ? { ...item, quantity: value } : item));
  }

  function detailPlaceholder(label: string) {
    const normalized = label || DETAIL_FIELD_OPTIONS[0];
    return DETAIL_PLACEHOLDERS[normalized] ?? 'Value';
  }

  function formatFieldLabel(label: string) {
    return label
      .replace(/_/g, ' ')
      .replace(/\b\w/g, (char) => char.toUpperCase());
  }

  function addItemDetail(index: number) {
    items = items.map((item, i) =>
      i === index
        ? {
            ...item,
            extras: [
              ...item.extras,
              { id: nextExtraFieldId(), label: DETAIL_FIELD_OPTIONS[0], value: '' }
            ]
          }
        : item
    );
  }

  function updateItemDetailLabel(index: number, detailId: number, value: string) {
    items = items.map((item, i) => {
      if (i !== index) {
        return item;
      }
      return {
        ...item,
        extras: item.extras.map((extra) =>
          extra.id === detailId ? { ...extra, label: value } : extra
        )
      };
    });
  }

  function updateItemDetailValue(index: number, detailId: number, value: string) {
    items = items.map((item, i) => {
      if (i !== index) {
        return item;
      }
      return {
        ...item,
        extras: item.extras.map((extra) =>
          extra.id === detailId ? { ...extra, value: value } : extra
        )
      };
    });
  }

  function removeItemDetail(index: number, detailId: number) {
    items = items.map((item, i) => {
      if (i !== index) {
        return item;
      }
      return {
        ...item,
        extras: item.extras.filter((extra) => extra.id !== detailId)
      };
    });
  }

  function qrCodeUrl(qr: string) {
    const user = get(userStore);
    const query = user ? `?mock_user=${encodeURIComponent(user.id)}` : '';
    return `${API_URL}/containers/${qr}/qrcode${query}`;
  }

  function handleQrScannerResult(result: string) {
    const trimmed = result.trim();
    if (!trimmed) {
      return;
    }

    newQrCode = trimmed;
  }

  let container_bool = false;
  $: reactive_container = container_bool;

  let name_bool = false;
  $: reactive_name = name_bool;

  let quan_bool = false;
  $: reactive_quan= quan_bool;

  function speech_individual_switch(target: VoiceTarget, switch_bool : boolean){
    console.log("speech_individual_switch");
    switch (target.kind) {
      case 'containerName':
        container_bool = switch_bool;
        return;
      case 'itemName':
        name_bool = switch_bool;
        return;
      case 'itemQuantity':
        quan_bool = switch_bool;
        return;
    }
  }

  function speech_all_off(){
    console.log("speech_all_off");
    container_bool = false;
    name_bool = false;
    quan_bool = false;
  }

</script>

<main class="page">
  <h1>PAQS Container Setup</h1>
  <p class="lead">“PEACE IN THE CHAOS”</p>
  <p class="sublead">QR-assisted packing and storage.</p>

  <section class="card create-card">
    <div class="toolbar">
      <a class="link-button" href="/">← Back to dashboard</a>
    </div>

    {#if !canCreate}
      <p class="permission-banner">
        You can browse container layouts, but only creator or admin personas can add new ones. Choose a different persona from the top-right switcher to continue.
      </p>
    {/if}

    <fieldset class="form-fieldset" disabled={!canCreate}>
      {#if speechSupportChecked && !speechSupported}
        <p class="voice-support">Voice input is not supported in this browser. You can continue typing manually.</p>
      {/if}
      {#if speechError}
        <p class="voice-support voice-error">{speechError}</p>
      {/if}

      <div class="input-group">
        <div class="field-header">
          <label for="container-name">Container name</label>
          {#if speechSupported}
            <button
              type="button"
              class={`voice-button${reactive_container ? ' active' : ''}`}
              onclick={() => toggleVoiceInput(containerVoiceTarget)}
            >
              {reactive_container ? 'Stop' : 'Use voice'}
            </button>
          {/if}
        </div>
        <input
          id="container-name"
          type="text"
          placeholder="e.g. Red Drawer"
          value={containerName}
          oninput={(event) => {
            containerName = (event.currentTarget as HTMLInputElement).value;
          }}
        />
        {#if reactive_container}
          <p class="voice-status">Listening…</p>
        {/if}
      </div>

      <div class="input-group">
        <label for="new-qr">QR code</label>
        <input
          id="new-qr"
          type="text"
          placeholder="e.g. QR-RED-DRAWER"
          value={newQrCode}
          oninput={(event) => {
            newQrCode = (event.currentTarget as HTMLInputElement).value;
          }}
        />
      </div>

      <QrScanner
        title="Scan a QR Code"
        description="Use your device camera to capture a pre-made QR label and auto-fill the code above."
        on:detect={(event) => handleQrScannerResult(event.detail.text)}
      >
        <svelte:fragment slot="tips">
          <ul>
            <li>Align the label until the QR code fills the frame.</li>
            <li>We’ll copy the detected code into the field above automatically.</li>
            <li>If you need a fresh label, complete the form and we’ll generate one.</li>
          </ul>
        </svelte:fragment>
      </QrScanner>

      {#each items as item, index}
        {@const nameTarget = { kind: 'itemName', index } as VoiceTarget}
        {@const quantityTarget = { kind: 'itemQuantity', index } as VoiceTarget}
        <div class="content-card form">
          <div class="item-header">
            <h2>Item {index + 1}</h2>
            {#if items.length > 1}
              <button type="button" class="remove-item" onclick={() => removeItem(index)}>
                Remove
              </button>
            {/if}
          </div>
          <div class="input-group">
            <div class="field-header">
              <label>Name</label>
              {#if speechSupported}
                <button
                  type="button"
                  class={`voice-button${reactive_name ? ' active' : ''}`}
                  onclick={() => toggleVoiceInput(nameTarget)}
                >
                  {reactive_name ? 'Stop' : 'Use voice'}
                </button>
              {/if}
            </div>
            <input
              type="text"
              value={item.name}
              placeholder="Item name"
              oninput={(event) =>
                updateItemName(index, (event.currentTarget as HTMLInputElement).value)
              }
            />
            {#if reactive_name}
              <p class="voice-status">Listening…</p>
            {/if}
          </div>
          <div class="input-group">
            <div class="field-header">
              <label>Quantity</label>
              {#if speechSupported}
                <button
                  type="button"
                  class={`voice-button${reactive_quan ? ' active' : ''}`}
                  onclick={() => toggleVoiceInput(quantityTarget)}
                >
                  {reactive_quan ? 'Stop' : 'Use voice'}
                </button>
              {/if}
            </div>
            <input
              type="number"
              min="0"
              step="1"
              inputmode="numeric"
              value={item.quantity}
              placeholder="0"
              oninput={(event) =>
                updateItemQuantity(index, (event.currentTarget as HTMLInputElement).value)
              }
            />
            {#if reactive_quan}
              <p class="voice-status">Listening…</p>
            {/if}
          </div>

          {#each item.extras as extra (extra.id)}
            <div class="input-group custom-detail">
              <div class="field-header">
                <label>Detail</label>
                <button
                  type="button"
                  class="remove-detail"
                  onclick={() => removeItemDetail(index, extra.id)}
                >
                  Remove
                </button>
              </div>
              <div class="custom-field-grid">
                <select
                  value={extra.label || DETAIL_FIELD_OPTIONS[0]}
                  onchange={(event) =>
                    updateItemDetailLabel(index, extra.id, (event.currentTarget as HTMLSelectElement).value)
                  }
                >
                  {#each DETAIL_FIELD_OPTIONS as option}
                    <option value={option}>{option}</option>
                  {/each}
                </select>
                <input
                  type="text"
                  placeholder={detailPlaceholder(extra.label)}
                  value={extra.value}
                  oninput={(event) =>
                    updateItemDetailValue(index, extra.id, (event.currentTarget as HTMLInputElement).value)
                  }
                />
              </div>
            </div>
          {/each}

          <button type="button" class="add-detail" onclick={() => addItemDetail(index)}>
            + Add detail
          </button>
        </div>
      {/each}

      <div class="form-actions">
        <button class="secondary" type="button" onclick={addItem}>+ Add another item</button>
        <button type="button" onclick={createContainer} disabled={saving}>
          {saving ? 'Saving…' : 'Save container'}
        </button>
      </div>
    </fieldset>

  {#if error}
    <p class="error">{error}</p>
  {:else if success}
    <p class="success">{success}</p>
  {/if}

  {#if deleteError}
    <p class="error">{deleteError}</p>
  {:else if deleteSuccess}
    <p class="success">{deleteSuccess}</p>
  {/if}
</section>

  {#if createdContainer}
    <section class="card preview-card">
      <h2>{createdContainer.name}</h2>
      <p class="qr-code-label">QR: {createdContainer.qr_code}</p>
      <p class="muted">QR created successfully. Print or download the code below.</p>

      {#each createdContainer.contents as item}
        {@const extras = previewItemExtras(item)}
        <div class="content-card">
          <div class="content-name">{item.name}</div>
          <div class="content-quantity">Quantity: {item.quantity}</div>
          {#if extras.length}
            <dl class="item-details">
              {#each extras as [label, value]}
                <div class="item-detail-row">
                  <dt>{label}</dt>
                  <dd>{value}</dd>
                </div>
              {/each}
            </dl>
          {/if}
        </div>
      {/each}

      <img src={qrCodeUrl(createdContainer.qr_code)} alt={`QR code for ${createdContainer.qr_code}`} />

      {#if canDeleteContainer}
        <button
          type="button"
          class="danger"
          onclick={() => {
            if (typeof window === 'undefined' || window.confirm(`Delete container ${createdContainer.qr_code}?`)) {
              deleteContainerByQr(createdContainer.qr_code);
            }
          }}
          disabled={deleteLoading}
        >
          {deleteLoading ? 'Deleting…' : 'Delete container'}
        </button>
      {/if}
    </section>
  {/if}
</main>

<style>
  .page {
    max-width: 860px;
    margin: 0 auto;
    padding: 48px 24px 80px;
  }

  h1 {
    text-align: center;
    font-size: 2.3rem;
    margin: 0;
    color: var(--color-text);
  }

  .lead {
    text-align: center;
    margin: 12px 0 8px;
    color: var(--color-text-muted);
    font-weight: 600;
    letter-spacing: 0.08em;
  }

  .sublead {
    text-align: center;
    margin: 0 0 36px;
    color: var(--color-text-muted);
  }

  .card {
    border-radius: 16px;
    padding: 24px;
    border: 1px solid var(--color-border);
    box-shadow: var(--shadow-card);
    background: var(--color-card-alt);
    color: var(--color-text);
  }

  .create-card {
    margin-bottom: 32px;
  }

  .toolbar {
    display: flex;
    justify-content: flex-end;
    margin-bottom: 12px;
  }

  .permission-banner {
    margin: 0 0 18px;
    padding: 12px 16px;
    border-radius: 12px;
    border: 1px solid var(--color-divider);
    background: var(--color-card-tertiary);
    color: var(--color-text);
    font-size: 0.95rem;
    line-height: 1.4;
  }

  .link-button {
    background: transparent;
    color: var(--color-primary);
    border: none;
    padding: 6px 12px;
    font-size: 0.95rem;
    text-decoration: underline;
    cursor: pointer;
  }

  .link-button:hover {
    color: var(--color-primary-hover);
  }

  fieldset {
    border: none;
    padding: 0;
    margin: 0;
  }

  .form-fieldset {
    display: flex;
    flex-direction: column;
    gap: 0;
  }

  .form-fieldset[disabled] {
    opacity: 0.6;
  }

  .input-group {
    display: flex;
    flex-direction: column;
    gap: 6px;
    margin-top: 16px;
  }

  .input-group label {
    font-weight: 600;
    color: var(--color-text);
  }

  .field-header {
    display: flex;
    justify-content: space-between;
    gap: 12px;
    align-items: center;
  }

  input,
  textarea,
  select {
    padding: 10px 12px;
    border-radius: 8px;
    border: 1px solid var(--color-divider);
    background: var(--color-card);
    color: var(--color-text);
    font-size: 1rem;
  }

  input:focus,
  textarea:focus,
  select:focus {
    outline: 2px solid var(--color-primary);
    outline-offset: 1px;
  }

  .voice-button {
    border: 1px solid var(--color-primary);
    background: transparent;
    color: var(--color-primary);
    border-radius: 999px;
    padding: 4px 12px;
    font-size: 0.85rem;
    cursor: pointer;
    transition: background 0.2s ease, color 0.2s ease;
  }

  .voice-button:hover {
    background: var(--color-primary-hover);
    color: var(--color-card, #ffffff);
  }

  .voice-button.active {
    background: var(--color-primary);
    color: var(--color-card, #ffffff);
  }

  .voice-status {
    margin: 4px 0 0;
    font-size: 0.85rem;
    color: var(--color-secondary);
  }

  .voice-support {
    margin: 12px 0 0;
    font-size: 0.9rem;
    color: var(--color-text-muted);
  }

  .voice-support.voice-error {
    color: var(--color-error, #b00020);
  }

  .custom-detail {
    margin-top: 12px;
  }

  .custom-field-grid {
    display: grid;
    gap: 8px;
    grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  }

  .content-card {
    border-radius: 12px;
    padding: 16px;
    border: 1px solid var(--color-divider);
    background: var(--color-card);
    margin-top: 16px;
  }

  .content-card.form {
    background: var(--color-card-tertiary);
  }

  .item-details {
    margin: 12px 0 0;
    display: grid;
    gap: 6px;
  }

  .item-detail-row {
    display: grid;
    grid-template-columns: minmax(120px, 1fr) 2fr;
    gap: 8px;
    padding: 8px 10px;
    background: var(--color-card);
    border-radius: 8px;
  }

  .item-detail-row dt {
    margin: 0;
    font-weight: 600;
    color: var(--color-text);
  }

  .item-detail-row dd {
    margin: 0;
    color: var(--color-text-muted);
  }

  .item-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .remove-item {
    background: transparent;
    border: none;
    color: var(--color-error, #b00020);
    font-size: 0.9rem;
    cursor: pointer;
  }

  .form-actions {
    display: flex;
    gap: 12px;
    justify-content: flex-end;
    margin-top: 24px;
  }

  .form-actions button {
    min-width: 160px;
  }

  button {
    border-radius: 999px;
    padding: 10px 18px;
    border: none;
    font-weight: 600;
    cursor: pointer;
    background: var(--color-primary);
    color: var(--color-card, #ffffff);
    transition: background 0.2s ease;
  }

  button.secondary {
    background: var(--color-secondary);
    color: var(--color-card, #ffffff);
  }

  button.danger {
    background: var(--color-danger, #c62828);
    color: #fff;
  }

  button.danger:hover {
    background: var(--color-danger-hover, #b71c1c);
  }

  button:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }

  button.remove-detail {
    background: transparent;
    color: var(--color-primary);
    border: none;
    padding: 2px 6px;
    font-size: 0.85rem;
  }

  button.remove-detail:hover {
    text-decoration: underline;
  }

  button.add-detail {
    background: transparent;
    color: var(--color-secondary);
    border: 1px dashed var(--color-secondary);
    margin-top: 12px;
    padding: 6px 14px;
  }

  button.add-detail:hover {
    background: var(--color-surface-overlay);
  }

  .error {
    margin-top: 16px;
    color: var(--color-error, #b00020);
    font-weight: 600;
  }

  .success {
    margin-top: 16px;
    color: var(--color-success, #0f8d6d);
    font-weight: 600;
  }

  .preview-card img {
    margin-top: 16px;
    max-width: 200px;
  }

  .content-name {
    font-weight: 600;
  }

  .content-quantity {
    margin-top: 4px;
    color: var(--color-text-muted);
  }
</style>
  let extraFieldId = 0;
