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

    func testLaunchNavigationAndClearControls() throws {
        let radarName = field("Nombre o apellido", id: "name")
        XCTAssertTrue(radarName.waitForExistence(timeout: 20), "Radar debe terminar de cargar.")
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
}
