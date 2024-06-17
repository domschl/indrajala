// The Swift Programming Language
// https://docs.swift.org/swift-book

import Foundation
import indralib

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
        if result != testCase.result {
          print("Failed for publish:\(testCase.publish), subscribe:\(testCase.subscribe)")
        }
      }
    } catch {
      print("Error reading JSON file: \(error)")
    }
  }

test_mqcmp()
