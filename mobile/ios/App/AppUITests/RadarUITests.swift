import XCTest

final class RadarUITests: XCTestCase {
    private let app = XCUIApplication()

    override func setUpWithError() throws {
        continueAfterFailure = false
        app.launchArguments = ["-AppleLanguages", "(es)", "-AppleLocale", "es_CO"]
        app.launch()
        XCTAssertTrue(app.webViews.firstMatch.waitForExistence(timeout: 20), "La interfaz debe abrir dentro de iOS.")
    }

    override func tearDownWithError() throws {
        let hierarchy = XCTAttachment(string: app.debugDescription)
        hierarchy.name = "Jerarquia de accesibilidad"
        hierarchy.lifetime = .deleteOnSuccess
        add(hierarchy)
    }

    private func control(_ label: String) -> XCUIElement {
        app.descendants(matching: .any).matching(NSPredicate(format: "label == %@", label)).firstMatch
    }

    private func field(_ label: String, id: String) -> XCUIElement {
        app.textFields.matching(NSPredicate(format: "label == %@ OR identifier == %@", label, id)).firstMatch
    }

    private func capture(_ name: String) {
        let attachment = XCTAttachment(screenshot: XCUIScreen.main.screenshot())
        attachment.name = name
        attachment.lifetime = .keepAlways
        add(attachment)
    }

    private func webViewport() -> CGRect {
        let bounds = app.frame
        let top = bounds.minY + 80
        var bottom = bounds.maxY - 50
        let keyboard = app.keyboards.firstMatch
        if keyboard.exists { bottom = min(bottom, keyboard.frame.minY - 10) }
        return CGRect(x: bounds.minX + 1, y: top, width: bounds.width - 2, height: max(1, bottom - top))
    }

    private func reveal(_ element: XCUIElement, upwards: Bool = true) {
        // WKWebView on iOS 26.5 can expose a valid visible frame while its
        // accessibility activation point is invalid. Scroll by actual bounds;
        // the assertions after each real touch still require the app to react.
        for _ in 0..<20 {
            let viewport = webViewport()
            let frame = element.exists ? element.frame : .zero
            if !frame.isEmpty && viewport.contains(frame) { return }
            let forward = !frame.isEmpty ? frame.midY > viewport.midY : upwards
            let origin = app.coordinate(withNormalizedOffset: .zero)
            let start = origin.withOffset(CGVector(dx: viewport.midX - app.frame.minX,
                dy: viewport.minY - app.frame.minY + viewport.height * (forward ? 0.8 : 0.25)))
            let end = origin.withOffset(CGVector(dx: viewport.midX - app.frame.minX,
                dy: viewport.minY - app.frame.minY + viewport.height * (forward ? 0.25 : 0.8)))
            start.press(forDuration: 0.05, thenDragTo: end)
        }
        XCTAssertTrue(element.exists && !element.frame.isEmpty && webViewport().contains(element.frame),
                      "El control debe poder alcanzarse desplazando la pantalla: \(element.label)")
    }

    private func tapWeb(_ element: XCUIElement) {
        reveal(element)
        element.coordinate(withNormalizedOffset: CGVector(dx: 0.5, dy: 0.5)).tap()
    }

    private func selectTab(_ name: String) {
        let tab = control(name)
        reveal(tab, upwards: false)
        tapWeb(tab)
        let selected = XCTNSPredicateExpectation(predicate: NSPredicate(format: "selected == true"), object: tab)
        XCTAssertEqual(XCTWaiter.wait(for: [selected], timeout: 10), .completed)
    }

    private func frameResult(_ firstControl: XCUIElement) {
        reveal(firstControl)
        // Position the beginning of the result below the safe area using real
        // scrolling, so the original screenshot retains the result's context.
        for _ in 0..<5 {
            let delta = firstControl.frame.minY - app.frame.minY - app.frame.height * 0.12
            if abs(delta) < 24 { return }
            let distance = min(abs(delta) / app.frame.height, 0.4)
            let startY: CGFloat = delta > 0 ? 0.75 : 0.25
            let endY = startY + (delta > 0 ? -distance : distance)
            let view = app.webViews.firstMatch
            view.coordinate(withNormalizedOffset: CGVector(dx: 0.5, dy: startY))
                .press(forDuration: 0.05, thenDragTo: view.coordinate(withNormalizedOffset: CGVector(dx: 0.5, dy: endY)))
        }
    }

    private func dismissKeyboard() {
        let done = app.toolbars.buttons.matching(NSPredicate(format: "label IN %@ OR identifier == 'Done'", ["OK", "Listo", "Done"])).firstMatch
        if done.exists && done.isHittable { done.tap() }
        else if app.keyboards.firstMatch.exists {
            app.webViews.firstMatch.swipeUp()
        }
    }

    private func cancelShare(_ name: String) {
        let share = control(name)
        reveal(share)
        tapWeb(share)
        let sheet = app.otherElements["ActivityListView"]
        XCTAssertTrue(sheet.waitForExistence(timeout: 20), "Debe abrir la hoja nativa para compartir.")
        capture(name == "Compartir reporte" ? "QA-Compartir-reporte" : "QA-Compartir-comparativo")
        let dismissRegion = app.otherElements["PopoverDismissRegion"]
        if dismissRegion.exists {
            // iOS 26 presents this activity controller as a popover; its
            // accessibility hierarchy exposes an outside dismissal region.
            dismissRegion.tap()
        } else {
            let close = app.buttons.matching(NSPredicate(format: "label IN %@ OR identifier == 'Close'", ["Cerrar", "Close", "Cancelar", "Cancel"])).firstMatch
            XCTAssertTrue(close.waitForExistence(timeout: 10))
            close.tap()
        }
        let closed = XCTNSPredicateExpectation(predicate: NSPredicate(format: "exists == false"), object: sheet)
        XCTAssertEqual(XCTWaiter.wait(for: [closed], timeout: 10), .completed)
        XCTAssertTrue(share.waitForExistence(timeout: 10), "Cancelar no debe perder el resultado.")
    }

    func testLaunchNavigationAndClearControls() throws {
        let radarName = field("Nombre o apellido", id: "name")
        // Initial WKWebView/accessibility setup is slower on a fresh hosted
        // simulator. The previous run exposed the ready form after 60 seconds.
        XCTAssertTrue(radarName.waitForExistence(timeout: 75), "Radar debe terminar de cargar.")
        let comparisonTab = control("COMPARATIVOS")
        XCTAssertTrue(comparisonTab.waitForExistence(timeout: 10))
        XCTAssertTrue(comparisonTab.isHittable)
        capture("01-Radar-iPhone")

        selectTab("COMPARATIVOS")
        let comparisonName = field("Agregar congresista", id: "compare-name")
        XCTAssertTrue(comparisonName.waitForExistence(timeout: 10))
        let ready = XCTNSPredicateExpectation(predicate: NSPredicate(format: "enabled == true"), object: comparisonName)
        XCTAssertEqual(XCTWaiter.wait(for: [ready], timeout: 15), .completed, "El directorio incluido debe habilitar la búsqueda.")
        let comparisonZone = field("Zona para todos", id: "compare-territory")
        XCTAssertEqual(comparisonZone.value as? String, "Colombia")
        capture("02-Comparativos-iPhone")

        comparisonName.tap()
        comparisonName.typeText("Toro")
        let clearComparisonName = control("Borrar nombre para comparar")
        XCTAssertTrue(clearComparisonName.waitForExistence(timeout: 5))
        tapWeb(clearComparisonName)
        XCTAssertTrue(comparisonName.value as? String == "" || comparisonName.value as? String == "Escribe un nombre o apellido")
        comparisonName.typeText("Lara")
        XCTAssertEqual(comparisonName.value as? String, "Lara", "Después de borrar se conserva el foco para escribir de nuevo.")
        tapWeb(clearComparisonName)

        let clearComparisonZone = control("Borrar zona para comparar")
        tapWeb(clearComparisonZone)
        XCTAssertTrue(comparisonZone.value as? String == "" || comparisonZone.value as? String == "Ej. Colombia o Antioquia")
        comparisonZone.typeText("Colombia")
        XCTAssertEqual(comparisonZone.value as? String, "Colombia")

        dismissKeyboard()
        selectTab("RADAR")
        XCTAssertTrue(radarName.waitForExistence(timeout: 10))
        radarName.tap()
        radarName.typeText("Toro")
        tapWeb(control("Borrar nombre"))
        XCTAssertTrue(radarName.value as? String == "" || radarName.value as? String == "Ej. Arizabaleta o Alejandro")
        let radarZone = field("Zona", id: "territory")
        tapWeb(control("Borrar zona"))
        XCTAssertTrue(radarZone.value as? String == "" || radarZone.value as? String == "Ej. Colombia o Antioquia")
        radarZone.typeText("Colombia")
        XCTAssertEqual(radarZone.value as? String, "Colombia")
    }

    private func generateLiveReport() -> XCUIElement {
        // Use the same public API and native plugins as the shipped app. No
        // response fixtures or synthetic results are injected into this test.
        selectTab("RADAR")
        let name = field("Nombre o apellido", id: "name")
        reveal(name, upwards: false)
        name.tap()
        if control("Borrar nombre").exists { tapWeb(control("Borrar nombre")) }
        name.typeText("Alejandro Toro")
        dismissKeyboard()
        let generate = control("GENERAR REPORTE")
        reveal(generate)
        tapWeb(generate)

        let source = app.links.matching(NSPredicate(format: "label BEGINSWITH %@", "Abrir fuente:")).firstMatch
        XCTAssertTrue(source.waitForExistence(timeout: 100), "La consulta real debe devolver al menos una noticia; un fallo de la fuente no se sustituye por datos inventados.")
        return source
    }

    func testSafariReturnKeepsReport() throws {
        let source = generateLiveReport()
        let originalSource = source.label
        reveal(source)
        tapWeb(source)
        // The observed iOS 26 Safari toolbar exposes Close instead of Done.
        // Match exact native identifiers to avoid a site's cookie-dialog button.
        let safariDone = app.buttons.matching(NSPredicate(format: "identifier IN %@ OR label IN %@", ["Close", "Done"], ["OK", "Listo", "Done", "Cerrar", "Close"])).firstMatch
        XCTAssertTrue(safariDone.waitForExistence(timeout: 20), "La fuente debe abrir en Safari integrado con salida a Radar.")
        capture("QA-Fuente-Safari")
        // A publisher's modal cookie dialog can trap accessibility focus in the
        // web page. Dismiss that dialog without accepting cookies before using
        // Safari's own toolbar, then require the actual return to Radar.
        let cookieClose = app.webViews.buttons.matching(NSPredicate(format: "label IN %@", ["Close dialog", "Cerrar diálogo", "NON ACCETTO", "Reject all", "Rechazar todo"])).firstMatch
        if cookieClose.exists && app.frame.contains(cookieClose.frame) {
            cookieClose.coordinate(withNormalizedOffset: CGVector(dx: 0.5, dy: 0.5)).tap()
        }
        let toolbarClose = app.otherElements["TopBrowserBar"].buttons["Close"]
        let closeControl = toolbarClose.exists ? toolbarClose : safariDone
        XCTAssertTrue(closeControl.exists && !closeControl.frame.isEmpty && app.frame.contains(closeControl.frame))
        closeControl.coordinate(withNormalizedOffset: CGVector(dx: 0.5, dy: 0.5)).tap()
        XCTAssertTrue(source.waitForExistence(timeout: 20), "Cerrar Safari debe devolver la consulta original.")
        XCTAssertEqual(source.label, originalSource, "Al cerrar Safari se conserva la noticia de la consulta.")

    }

    func testLiveReportComparisonAndNativeActions() throws {
        let source = generateLiveReport()
        let originalSource = source.label
        frameResult(control("Compartir reporte"))
        capture("03-Reporte-real-iPhone")
        cancelShare("Compartir reporte")

        app.terminate()
        app.launch()
        XCTAssertTrue(source.waitForExistence(timeout: 20), "El reporte debe recuperarse de Preferences tras cerrar la app.")
        XCTAssertEqual(source.label, originalSource)
        let restored = app.staticTexts.matching(NSPredicate(format: "label BEGINSWITH %@", "Consulta recuperada")).firstMatch
        XCTAssertTrue(restored.waitForExistence(timeout: 10))
        reveal(restored, upwards: false)
        capture("QA-Reporte-recuperado")

        selectTab("COMPARATIVOS")
        let comparisonName = field("Agregar congresista", id: "compare-name")
        for (query, expected) in [("Alejandro Toro", "Toro Ramírez, David Alejandro"), ("Iván Cepeda", "Cepeda Castro, Iván")] {
            reveal(comparisonName, upwards: false)
            // Let XCTest focus text inputs through the keyboard-aware tap;
            // coordinate touches are reserved for the affected web controls.
            comparisonName.tap()
            comparisonName.typeText(query)
            let entered = XCTNSPredicateExpectation(predicate: NSPredicate(format: "value == %@", query), object: comparisonName)
            XCTAssertEqual(XCTWaiter.wait(for: [entered], timeout: 10), .completed, "El campo debe recibir el nombre antes de buscarlo.")
            let option = app.descendants(matching: .any).matching(NSPredicate(format: "label BEGINSWITH %@", expected)).firstMatch
            XCTAssertTrue(option.waitForExistence(timeout: 10), "El congresista debe estar en el directorio incluido.")
            tapWeb(option)
        }
        dismissKeyboard()
        let compare = control("COMPARAR MENCIONES")
        reveal(compare)
        XCTAssertTrue(compare.isEnabled)
        tapWeb(compare)
        let comparisonShare = control("Compartir comparativo")
        XCTAssertTrue(comparisonShare.waitForExistence(timeout: 100), "Comparativos debe terminar con los datos reales y los fallos que correspondan.")
        frameResult(comparisonShare)
        capture("04-Comparativo-real-iPhone")
        cancelShare("Compartir comparativo")

        app.terminate()
        app.launch()
        XCTAssertTrue(comparisonShare.waitForExistence(timeout: 20), "La pestaña y el comparativo deben recuperarse al reabrir.")

        let settings = control("Soporte, privacidad y datos guardados")
        reveal(settings)
        tapWeb(settings)
        let privacy = control("Privacidad")
        reveal(privacy)
        tapWeb(privacy)
        XCTAssertTrue(control("Privacidad de Radar Político").waitForExistence(timeout: 10))
        tapWeb(control("← Volver a Radar"))
        XCTAssertTrue(comparisonShare.waitForExistence(timeout: 20), "Volver de privacidad debe recuperar el comparativo.")
        reveal(settings)
        tapWeb(settings)
        let clear = control("Borrar consultas guardadas")
        reveal(clear)
        tapWeb(clear)
        let confirm = app.alerts.buttons.matching(NSPredicate(format: "label IN %@", ["OK", "Aceptar", "Borrar"])).firstMatch
        XCTAssertTrue(confirm.waitForExistence(timeout: 10))
        confirm.tap()
        XCTAssertTrue(field("Nombre o apellido", id: "name").waitForExistence(timeout: 20))
        app.terminate()
        app.launch()
        XCTAssertTrue(field("Nombre o apellido", id: "name").waitForExistence(timeout: 20))
        XCTAssertFalse(source.exists, "La consulta borrada no debe reaparecer al abrir la app.")
        selectTab("COMPARATIVOS")
        XCTAssertFalse(comparisonShare.exists, "El comparativo borrado tampoco debe reaparecer.")
    }
}
