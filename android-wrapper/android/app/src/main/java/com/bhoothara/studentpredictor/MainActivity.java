package com.bhoothara.studentpredictor;

import android.os.Bundle;
import android.webkit.ValueCallback;
import com.getcapacitor.BridgeActivity;
import com.getcapacitor.Plugin;
import android.util.Log;

/**
 * MainActivity: ensures webview content is pushed below the Android status bar.
 * Keeps a single class and correct package name.
 */
public class MainActivity extends BridgeActivity {

    private static final String TAG = "MainActivity";

    @Override
    public void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        // Calculate status bar height and inject JS after the WebView is ready
        int statusBarHeight = 0;
        int resourceId = getResources().getIdentifier("status_bar_height", "dimen", "android");
        if (resourceId > 0) {
            statusBarHeight = getResources().getDimensionPixelSize(resourceId);
        }

        // prepare JS to add top padding to body so navbar sits below the status bar
        final String js = "document && (document.body.style.paddingTop = '" + statusBarHeight + "px');";

        // Wait until the Capacitor bridge & WebView are available, then run the JS
        getBridge().getWebView().post(() -> {
            try {
                // evaluateJavascript is available on the WebView; callback optional
                getBridge().getWebView().evaluateJavascript(js, new ValueCallback<String>() {
                    @Override
                    public void onReceiveValue(String value) {
                        // noop
                    }
                });
            } catch (Exception e) {
                Log.w(TAG, "Failed to inject status bar padding JS", e);
            }
        });
    }
}
