import Foundation
import XCTest

@testable import indralib

final class indralibTests: XCTestCase {
  struct TestData: Codable {
    let publish: String
    let subscribe: String
    let result: Bool
  }
  func test_mqcmp() {
    // Read mqcmp_data.json file in current directory (no bundle) with test data:
    // format: [ { "publish": "abc", "subscribe": "abc", "result": true}, ...]
    let fileURL = URL(fileURLWithPath: "mqcmp_data.json")
    do {
      // Read the JSON data from the file
      let jsonData = try Data(contentsOf: fileURL)
      // Decode the JSON data using JSONDecoder
      let decoder = JSONDecoder()
      let testCases = try decoder.decode([TestData].self, from: jsonData)
      // Process the tesst data
      for testCase in testCases {
        let result = IndraEvent.mqcmp(pub: testCase.publish, sub: testCase.subscribe)

        XCTAssertEqual(
          result, testCase.result,
          "Failed for publish:\(testCase.publish), subscribe:\(testCase.subscribe)")
      }
    } catch {
      print("Error reading JSON file: \(error)")
      XCTFail("Error reading JSON file: \(error)")
    }
  }

  func testIndraEventSerialization() {
    let event = IndraEvent()
    event.domain = "test.domain"
    event.from_id = "test.from_id"
    event.to_scope = "test.to_scope"
    event.data_type = "test.data_type"
    event.data = "{\"key\": \"value\"}"
    event.auth_hash = "test.auth_hash"

    // Convert event to JSON string
    guard let jsonString = event.to_json() else {
      XCTFail("Failed to convert IndraEvent to JSON")
      return
    }

    // Convert JSON string back to IndraEvent object
    guard let decodedEvent = IndraEvent.from_json(json_str: jsonString) else {
      XCTFail("Failed to convert JSON to IndraEvent")
      return
    }

    // Assert that the decoded event matches the original event
    XCTAssertEqual(decodedEvent.domain, event.domain)
    XCTAssertEqual(decodedEvent.from_id, event.from_id)
    XCTAssertEqual(decodedEvent.to_scope, event.to_scope)
    XCTAssertEqual(decodedEvent.data_type, event.data_type)
    XCTAssertEqual(decodedEvent.data, event.data)
    XCTAssertEqual(decodedEvent.auth_hash, event.auth_hash)
  }

  static var allTests = [
    ("test_mqcmp", test_mqcmp),
    ("testIndraEventSerialization", testIndraEventSerialization),
  ]
}
