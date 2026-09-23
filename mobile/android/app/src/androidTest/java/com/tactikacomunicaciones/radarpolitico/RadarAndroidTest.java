package com.tactikacomunicaciones.radarpolitico;

import static org.junit.Assert.*;
import static androidx.test.espresso.web.sugar.Web.onWebView;
import static androidx.test.espresso.web.webdriver.DriverAtoms.*;
import static androidx.test.espresso.intent.Intents.*;
import static androidx.test.espresso.intent.matcher.IntentMatchers.*;
import static org.hamcrest.Matchers.*;

import android.app.Activity;
import android.app.Instrumentation.ActivityResult;
import android.content.Intent;
import android.os.SystemClock;
import androidx.test.core.app.ActivityScenario;
import androidx.test.ext.junit.runners.AndroidJUnit4;
import androidx.test.platform.app.InstrumentationRegistry;
import androidx.test.espresso.web.webdriver.Locator;
import org.junit.*;
import org.junit.runner.RunWith;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicReference;

/** Native WebView/plugin regression checks. Report fixtures are explicitly synthetic. */
@RunWith(AndroidJUnit4.class)
public class RadarAndroidTest {
    private ActivityScenario<MainActivity> scenario;

    @Before public void launch() {
        InstrumentationRegistry.getInstrumentation().getTargetContext()
            .getSharedPreferences("CapacitorStorage", 0).edit().clear().commit();
        scenario = ActivityScenario.launch(MainActivity.class);
        waitFor("window.RadarNative && document.getElementById('native-starting').hidden", 20000);
    }

    @After public void close() { if (scenario != null) scenario.close(); }

    private String js(String source) {
        AtomicReference<String> result = new AtomicReference<>();
        CountDownLatch done = new CountDownLatch(1);
        scenario.onActivity(activity -> activity.getBridge().getWebView().evaluateJavascript(source, value -> {
            result.set(value); done.countDown();
        }));
        try { assertTrue("JavaScript callback", done.await(10, TimeUnit.SECONDS)); }
        catch (InterruptedException e) { throw new AssertionError(e); }
        return result.get();
    }

    private void waitFor(String expression, long timeout) {
        long deadline = SystemClock.elapsedRealtime() + timeout;
        while (SystemClock.elapsedRealtime() < deadline) {
            if ("true".equals(js("Boolean(" + expression + ")"))) return;
            SystemClock.sleep(100);
        }
        fail("Timed out: " + expression + " at " + js("location.href"));
    }

    private void fixtureReport() {
        js("""
          window.__end = new Date(Date.now()-60000).toISOString();
          window.RadarNative.request = async (path, options={}) => {
            if (path === '/api/search/window') return {ok:true,json:async()=>({end_time:window.__end})};
            return {ok:true,json:async()=>({
              items:[{title:'Noticia de prueba de compatibilidad',url:'https://example.org/',source:'Prueba',
                published:new Date(Date.parse(window.__end)-3600000).toISOString(),sentiment:'Neutral'}],
              web_coverage:{status:'available',limited:false},mentions:{web:1}
            })};
          };
          document.getElementById('name').value='Persona de prueba';
          document.getElementById('days').value='1';
          """);
        onWebView().withElement(findElement(Locator.CSS_SELECTOR, "button[onclick='go()']")).perform(webClick());
        waitFor("document.getElementById('mweb').textContent === '1'", 15000);
        js("window.__flushed=false; window.RadarNative.storage.flush().then(()=>window.__flushed=true)");
        waitFor("window.__flushed", 10000);
    }

    private void waitForIntent(org.hamcrest.Matcher<Intent> matcher) {
        long deadline = SystemClock.elapsedRealtime() + 10000;
        while (SystemClock.elapsedRealtime() < deadline) {
            InstrumentationRegistry.getInstrumentation().waitForIdleSync();
            if (getIntents().stream().anyMatch(matcher::matches)) {
                intended(matcher);
                return;
            }
            SystemClock.sleep(100);
        }
        intended(matcher);
    }

    @Test public void nativeHttpCanReadProductionSearchWindow() {
        js("window.RadarNative.request('/api/search/window', {cache:'no-store'}).then(async r=>{window.__http=r.ok && Number.isFinite(Date.parse((await r.json()).end_time));}).catch(e=>window.__httpError=String(e))");
        waitFor("window.__http === true || window.__httpError", 90000);
        assertEquals("Native HTTP: " + js("window.__httpError"), "true", js("window.__http"));
    }

    @Test public void reportSharesThroughAndroidAndSurvivesRecreation() {
        fixtureReport();
        init();
        try {
            intending(hasAction(Intent.ACTION_CHOOSER)).respondWith(new ActivityResult(Activity.RESULT_CANCELED, null));
            onWebView().withElement(findElement(Locator.ID, "native-share-report")).perform(webClick());
            waitFor("!document.getElementById('native-share-report').disabled", 10000);
            intended(hasAction(Intent.ACTION_CHOOSER));
            intending(hasAction(Intent.ACTION_VIEW)).respondWith(new ActivityResult(Activity.RESULT_CANCELED, null));
            onWebView().withElement(findElement(Locator.CSS_SELECTOR, "#items a")).perform(webClick());
            // Browser first starts its controller Activity, then the custom tab.
            waitForIntent(allOf(hasAction(Intent.ACTION_VIEW), hasData("https://example.org/")));
            assertEquals("\"https://localhost/\"", js("location.href"));
            js("window.__browserClosed=false;window.Capacitor.Plugins.Browser.close().then(()=>window.__browserClosed=true)");
            waitFor("window.__browserClosed", 10000);
        } finally { release(); }
        scenario.recreate();
        waitFor("document.getElementById('native-starting').hidden && document.getElementById('mweb').textContent === '1'", 20000);
        assertEquals("true", js("document.getElementById('report-restored').textContent.includes('Consulta recuperada')"));
        assertEquals("true", js("document.getElementById('items').textContent.includes('Noticia de prueba de compatibilidad')"));
        js("window.__cleared=false;window.RadarNative.storage.clearSaved().then(()=>window.__cleared=true)");
        waitFor("window.__cleared",10000);
        scenario.recreate();
        waitFor("document.getElementById('native-starting').hidden",20000);
        assertEquals("true",js("document.getElementById('result').classList.contains('hide')"));
    }

    @Test public void privacyStaysLocalAndBackReturnsToRadar() {
        js("document.getElementById('native-settings').open=true");
        onWebView().withElement(findElement(Locator.CSS_SELECTOR, "a[href='/privacy.html']")).perform(webClick());
        waitFor("location.pathname === '/privacy.html' && document.querySelector('h1')", 10000);
        assertEquals("\"https://localhost\"",js("location.origin"));
        // Android 16 does not dispatch the legacy KEYCODE_BACK injected by
        // Espresso.pressBack. Exercise the AndroidX callback used by system Back.
        scenario.onActivity(activity -> activity.getOnBackPressedDispatcher().onBackPressed());
        waitFor("document.getElementById('native-starting')?.hidden", 10000);
        js("document.getElementById('native-settings').open=true");
        onWebView().withElement(findElement(Locator.CSS_SELECTOR, "a[href='/privacy.html']")).perform(webClick());
        waitFor("location.pathname === '/privacy.html' && document.querySelector('h1')", 10000);
        onWebView().withElement(findElement(Locator.CSS_SELECTOR, ".back")).perform(webClick());
        waitFor("document.getElementById('native-starting')?.hidden", 10000);
        js("window.showTab('compare')");
        // Keep the real history from privacy: Back on the root must change tabs,
        // rather than reopening the previous legal page.
        scenario.onActivity(activity -> activity.getOnBackPressedDispatcher().onBackPressed());
        waitFor("document.getElementById('report-tab').getAttribute('aria-selected') === 'true'",10000);
    }
}
