import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig, type PluginOption, type PreviewServer, type ViteDevServer } from 'vite';

type PrintableServer =
	| Pick<ViteDevServer, 'printUrls' | 'resolvedUrls' | 'config'>
	| Pick<PreviewServer, 'printUrls' | 'resolvedUrls' | 'config'>;

const disableNetworkLogPlugin = (): PluginOption => ({
	name: 'local-url-logging',
	configureServer(server) {
		overridePrintUrls(server);
	},
	configurePreviewServer(server) {
		overridePrintUrls(server);
	}
});

function overridePrintUrls(server: PrintableServer) {
	const originalPrintUrls = server.printUrls;
	server.printUrls = () => {
		const localUrls = server.resolvedUrls?.local;
		if (!localUrls?.length) {
			originalPrintUrls();
			return;
		}

		for (const url of localUrls) {
			server.config.logger.info(`  ➜  Local:   ${url}`);
		}
	};
}

export default defineConfig({
	plugins: [sveltekit(), disableNetworkLogPlugin()],
	server: {
		host: process.env.HOST ?? '127.0.0.1'
	},
	preview: {
		host: process.env.HOST ?? '127.0.0.1'
	}
});
