// See https://svelte.dev/docs/kit/types#app.d.ts
// for information about these interfaces
declare global {
	namespace App {
		// interface Error {}
		// interface Locals {}
		// interface PageData {}
		// interface PageState {}
		// interface Platform {}
	}

	interface SpeechRecognition extends EventTarget {
		lang: string;
		interimResults: boolean;
		continuous: boolean;
		maxAlternatives: number;
		start(): void;
		stop(): void;
		abort(): void;
		onerror: ((event: SpeechRecognitionErrorEvent) => void) | null;
		onend: (() => void) | null;
		onresult: ((event: SpeechRecognitionEvent) => void) | null;
	}

	interface SpeechRecognitionEvent extends Event {
		results: SpeechRecognitionResultList;
	}

	interface SpeechRecognitionResultList {
		length: number;
		item(index: number): SpeechRecognitionResult;
		[index: number]: SpeechRecognitionResult;
	}

	interface SpeechRecognitionResult {
		isFinal: boolean;
		length: number;
		item(index: number): SpeechRecognitionAlternative;
		[index: number]: SpeechRecognitionAlternative;
	}

	interface SpeechRecognitionAlternative {
		transcript: string;
		confidence: number;
	}

	interface SpeechRecognitionErrorEvent extends Event {
		error: string;
		message: string;
	}

	type SpeechRecognitionConstructor = new () => SpeechRecognition;

	interface Window {
		SpeechRecognition?: SpeechRecognitionConstructor;
		webkitSpeechRecognition?: SpeechRecognitionConstructor;
	}
}

export {};
