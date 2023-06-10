import XCTest
@testable import indralib

final class indralibTests: XCTestCase {
    func test_mqcmp() {
        let testCases: [(String, String, Bool)] = [
            ("abc", "abc", true),
            ("ab", "abc", false),
            ("ab", "ab+", true),
            ("abcd/dfew", "abcd", false),
            ("ba", "bdc/ds", false),
            ("abc/def", "abc/+", true),
            ("abc/def", "asdf/+/asdf", false),
            ("abc/def/asdf", "abc/+/asdf", true),
            ("abc/def/ghi", "+/+/+", true),
            ("abc/def/ghi", "+/+/", false),
            ("abc/def/ghi", "+/+/+/+", false),
            ("abc/def/ghi", "+/#", true),
            ("abc/def/ghi", "+/+/#", true),
            ("abc/def/ghi", "+/+/+/#", false)
        ]
        
        for testCase in testCases {
            let pub = testCase.0
            let sub = testCase.1
            let expected = testCase.2
            
            let result = IndraEvent.mqcmp(pub: pub, sub: sub)
            
            XCTAssertEqual(result, expected, "Failed for pub:\(pub), sub:\(sub)")
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
        ("testIndraEventSerialization", testIndraEventSerialization)
    ]
}
