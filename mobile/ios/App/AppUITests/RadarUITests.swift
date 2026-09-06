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

    private func reveal(_ element: XCUIElement, upwards: Bool = true) {
        for _ in 0..<20 {
            if element.exists && element.isHittable { return }
            let view = app.webViews.firstMatch
            let forward = element.exists && element.frame.height > 0 ? element.frame.midY > app.frame.midY : upwards
            let start = view.coordinate(withNormalizedOffset: CGVector(dx: 0.5, dy: forward ? 0.75 : 0.3))
            let end = view.coordinate(withNormalizedOffset: CGVector(dx: 0.5, dy: forward ? 0.35 : 0.75))
            start.press(forDuration: 0.05, thenDragTo: end)
        }
        XCTAssertTrue(element.isHittable, "El control debe poder alcanzarse desplazando la pantalla: \(element.label)")
    }

    private func selectTab(_ name: String) {
        let tab = control(name)
        reveal(tab, upwards: false)
        tab.tap()
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
        share.tap()
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

        comparisonTab.tap()
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
        clearComparisonName.tap()
        XCTAssertTrue(comparisonName.value as? String == "" || comparisonName.value as? String == "Escribe un nombre o apellido")
        comparisonName.typeText("Lara")
        XCTAssertEqual(comparisonName.value as? String, "Lara", "Después de borrar se conserva el foco para escribir de nuevo.")
        clearComparisonName.tap()

        let clearComparisonZone = control("Borrar zona para comparar")
        clearComparisonZone.tap()
        XCTAssertTrue(comparisonZone.value as? String == "" || comparisonZone.value as? String == "Ej. Colombia o Antioquia")
        comparisonZone.typeText("Colombia")
        XCTAssertEqual(comparisonZone.value as? String, "Colombia")

        control("RADAR").tap()
        XCTAssertTrue(radarName.waitForExistence(timeout: 10))
        radarName.tap()
        radarName.typeText("Toro")
        control("Borrar nombre").tap()
        XCTAssertTrue(radarName.value as? String == "" || radarName.value as? String == "Ej. Toro o Alejandro")
        let radarZone = field("Zona", id: "territory")
        control("Borrar zona").tap()
        XCTAssertTrue(radarZone.value as? String == "" || radarZone.value as? String == "Ej. Colombia o Antioquia")
        radarZone.typeText("Colombia")
        XCTAssertEqual(radarZone.value as? String, "Colombia")
    }

    func testLiveReportComparisonAndNativeActions() throws {
        // Use the same public API and native plugins as the shipped app. No
        // response fixtures or synthetic results are injected into this test.
        selectTab("RADAR")
        let name = field("Nombre o apellido", id: "name")
        reveal(name, upwards: false)
        name.tap()
        if control("Borrar nombre").isHittable { control("Borrar nombre").tap() }
        name.typeText("Alejandro Toro")
        dismissKeyboard()
        let generate = control("GENERAR REPORTE")
        reveal(generate)
        generate.tap()

        let source = app.links.matching(NSPredicate(format: "label BEGINSWITH %@", "Abrir fuente:")).firstMatch
        XCTAssertTrue(source.waitForExistence(timeout: 100), "La consulta real debe devolver al menos una noticia; un fallo de la fuente no se sustituye por datos inventados.")
        let originalSource = source.label
        reveal(control("Compartir reporte"))
        app.webViews.firstMatch.swipeUp()
        capture("03-Reporte-real-iPhone")
        cancelShare("Compartir reporte")
        reveal(source)
        source.tap()
        let safariDone = app.buttons.matching(NSPredicate(format: "identifier == 'Done' OR label IN %@", ["OK", "Listo", "Done"])).firstMatch
        XCTAssertTrue(safariDone.waitForExistence(timeout: 20), "La fuente debe abrir en Safari integrado con salida a Radar.")
        capture("QA-Fuente-Safari")
        safariDone.tap()
        XCTAssertTrue(source.waitForExistence(timeout: 10))
        XCTAssertEqual(source.label, originalSource, "Al cerrar Safari se conserva la noticia de la consulta.")

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
            comparisonName.tap()
            comparisonName.typeText(query)
            let option = app.descendants(matching: .any).matching(NSPredicate(format: "label BEGINSWITH %@", expected)).firstMatch
            XCTAssertTrue(option.waitForExistence(timeout: 10), "El congresista debe estar en el directorio incluido.")
            option.tap()
        }
        dismissKeyboard()
        let compare = control("COMPARAR MENCIONES")
        reveal(compare)
        XCTAssertTrue(compare.isEnabled)
        compare.tap()
        let comparisonShare = control("Compartir comparativo")
        XCTAssertTrue(comparisonShare.waitForExistence(timeout: 100), "Comparativos debe terminar con los datos reales y los fallos que correspondan.")
        reveal(comparisonShare)
        app.webViews.firstMatch.swipeUp()
        capture("04-Comparativo-real-iPhone")
        cancelShare("Compartir comparativo")

        app.terminate()
        app.launch()
        XCTAssertTrue(comparisonShare.waitForExistence(timeout: 20), "La pestaña y el comparativo deben recuperarse al reabrir.")

        let settings = control("Soporte, privacidad y datos guardados")
        reveal(settings)
        settings.tap()
        let privacy = control("Privacidad")
        reveal(privacy)
        privacy.tap()
        XCTAssertTrue(control("Privacidad de Radar Político").waitForExistence(timeout: 10))
        control("← Volver a Radar").tap()
        XCTAssertTrue(comparisonShare.waitForExistence(timeout: 20), "Volver de privacidad debe recuperar el comparativo.")
        reveal(settings)
        settings.tap()
        let clear = control("Borrar consultas guardadas")
        reveal(clear)
        clear.tap()
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
