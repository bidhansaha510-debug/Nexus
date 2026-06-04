import type { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
    appId: 'com.nexus.ai.mobile',
    appName: 'NEXUS AI',
    webDir: 'www',
    server: {
        // Allow loading external URLs (the NEXUS server)
        allowNavigation: ['*', 'nexusaisystems.qzz.io'],
        cleartext: true, // Allow HTTP (non-HTTPS) connections for local servers
    },
    android: {
        allowMixedContent: true,
        backgroundColor: '#060810',
        buildOptions: {
            releaseType: 'APK',
        },
    },
    plugins: {
        SplashScreen: {
            // Disabled native splash — using custom HTML splash animation
            launchShowDuration: 0,
            backgroundColor: '#060810',
            showSpinner: false,
        },
        StatusBar: {
            style: 'DARK',
            backgroundColor: '#060810',
        },
    },
};

export default config;

