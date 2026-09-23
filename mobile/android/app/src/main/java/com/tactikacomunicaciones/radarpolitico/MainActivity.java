package com.tactikacomunicaciones.radarpolitico;

import android.net.Uri;
import android.os.Bundle;
import androidx.activity.OnBackPressedCallback;
import com.getcapacitor.BridgeActivity;
import java.util.Objects;

public class MainActivity extends BridgeActivity {
    @Override public void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        getOnBackPressedDispatcher().addCallback(this, new OnBackPressedCallback(true) {
            @Override public void handleOnBackPressed() {
                String current = getBridge().getWebView().getUrl();
                if (current != null) {
                    Uri page = Uri.parse(current);
                    Uri root = Uri.parse(getBridge().getAppUrl());
                    boolean local = Objects.equals(page.getScheme(), root.getScheme())
                        && Objects.equals(page.getAuthority(), root.getAuthority());
                    if (local && ("/privacy.html".equals(page.getPath()) || "/support.html".equals(page.getPath()))) {
                        // Legal documents have no app bootstrap/back listener.
                        // Return explicitly, including when WebView has no history.
                        getBridge().getWebView().loadUrl(getBridge().getAppUrl());
                        return;
                    }
                }
                // Radar's App plugin handles tabs, saved state and minimization.
                setEnabled(false);
                try { getOnBackPressedDispatcher().onBackPressed(); }
                finally { setEnabled(true); }
            }
        });
    }
}
