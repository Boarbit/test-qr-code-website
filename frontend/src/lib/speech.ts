export type SpeechRecognitionInit = Partial<Pick<SpeechRecognition, 'lang' | 'interimResults' | 'continuous' | 'maxAlternatives'>>;

function getCtor(): SpeechRecognitionConstructor | null {
  if (typeof window === 'undefined') {
    return null;
  }
  const ctor = window.SpeechRecognition ?? window.webkitSpeechRecognition ?? null;
  return ctor;
}

export function isSpeechRecognitionSupported(): boolean {
  return getCtor() !== null;
}

export function createSpeechRecognition(init: SpeechRecognitionInit = {}): SpeechRecognition | null {
  const ctor = getCtor();
  if (!ctor) {
    return null;
  }

  const recognition = new ctor();
  recognition.lang = init.lang ?? 'en-US';
  recognition.interimResults = init.interimResults ?? false;
  recognition.continuous = init.continuous ?? false;
  recognition.maxAlternatives = init.maxAlternatives ?? 1;
  return recognition;
}
