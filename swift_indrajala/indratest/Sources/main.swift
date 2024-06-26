// The Swift Programming Language
// https://docs.swift.org/swift-book

import Foundation
import indralib

struct DomainTestData: Codable {
  let publish: String
  let subscribe: String
  let result: Bool
}

struct TimeTestData: Codable {
  let Calendar: String
  let RD: Double
  let JulianDate: Double
  let julian_string: String
  let gregorian_string: String
}

struct result_block: Codable {
  var num_ok: Int
  var num_failed: Int
  var num_skipped: Int
  var errors: [String]
}

func test_mqcmp(folder: String = "../../test_data", checkFailures: Bool = false) -> result_block {
  var res: result_block = result_block(num_ok: 0, num_failed: 0, num_skipped: 0, errors: [])
  // Read mqcmp_data.json file in current directory (no bundle) with test data:
  // format: [ { "publish": "abc", "subscribe": "abc", "result": true}, ...]
  let filePath: String
  if checkFailures == false {
    filePath = "\(folder)/domain/domain_publish_subscribe_data.json"
  } else {
    filePath = "\(folder)/domain/domain_failure_cases.json"
  }
  // check if file exists
  let fileManager = FileManager.default
  if !fileManager.fileExists(atPath: filePath) {
    print("File not found: \(filePath)")
    res.num_failed += 1
    res.errors.append("Test data file not found: \(filePath)")
    return res
  }
  print("Reading test data from file: \(filePath)")
  let fileURL = URL(fileURLWithPath: filePath)

  let testCases: [DomainTestData]
  do {
    // Read the JSON data from the file, return error on failure:
    let jsonData = try Data(contentsOf: fileURL)
    // Decode the JSON data using JSONDecoder
    let decoder = JSONDecoder()
    testCases = try decoder.decode([DomainTestData].self, from: jsonData)
  } catch {
    print("Error reading JSON data from file: \(error)")
    res.num_failed += 1
    res.errors.append("Error reading JSON data from file: \(error)")
    return res
  }
  // Process the test data
  for testCase: DomainTestData in testCases {
    let result = IndraEvent.mqcmp(pub: testCase.publish, sub: testCase.subscribe)
    if result != testCase.result {
      print("Failed for publish:\(testCase.publish), subscribe:\(testCase.subscribe)")
      res.num_failed += 1
      res.errors.append("Failed for publish:\(testCase.publish), subscribe:\(testCase.subscribe)")
    } else {
      res.num_ok += 1
    }
  }
  return res
}

func cmp_time(d1: String, d2: String) -> Bool {
  let l1 = d1.count
  let l2 = d2.count
  var d1_ = d1
  var d2_ = d2
  if l1 < l2 {
    d2_ = String(d2.prefix(l1))
  }
  if l2 < l1 {
    d1_ = String(d1.prefix(l2))
  }
  return d1_ == d2_
}

func test_time(folder: String = "../../test_data", checkFailures: Bool = false) -> result_block {
  var res: result_block = result_block(num_ok: 0, num_failed: 0, num_skipped: 0, errors: [])
  // Read mqcmp_data.json file in current directory (no bundle) with test data:
  // format: [ { "publish": "abc", "subscribe": "abc", "result": true}, ...]
  let filePath: String
  if checkFailures == false {
    filePath = "\(folder)/time/normalized_jd_time_data.json"
  } else {
    res.num_failed += 1
    res.errors.append("Failure cases not implemented for time")
    return res
  }
  print("Reading test data from file: \(filePath)")
  // check if file exists
  let fileManager = FileManager.default
  if !fileManager.fileExists(atPath: filePath) {
    print("File not found: \(filePath)")
    res.num_failed += 1
    res.errors.append("Test data file not found: \(filePath)")
    return res
  }
  let fileURL = URL(fileURLWithPath: filePath)

  let testCases: [TimeTestData]
  do {
    // Read the JSON data from the file, return error on failure:
    let jsonData = try Data(contentsOf: fileURL)
    // Decode the JSON data using JSONDecoder
    let decoder = JSONDecoder()
    testCases = try decoder.decode([TimeTestData].self, from: jsonData)
  } catch {
    print("Error reading JSON data from file: \(error)")
    res.num_failed += 1
    res.errors.append("Error reading JSON data from file: \(error)")
    return res
  }
  // Process the test data
  for testCase: TimeTestData in testCases {
    let dit = IndraEvent.julianToISO(jd: testCase.JulianDate)
    let dij = IndraEvent.ISOToJulian(iso: dit)!
    // let dih: String = IndraEvent.julianToStringTime(jd: testCase.JulianDate)
    // if dit ends with " BC"
    var it = dit
    if it.hasSuffix(" BC") {
      it = "-" + it.prefix(it.count - 3)
    }
    if cmp_time(d1: dit, d2: it) == false {
      print("Failed for JulianDate:\(testCase.JulianDate), julian_string:\(testCase.julian_string)")
      res.num_failed += 1
      res.errors.append(
        "Failed for JulianDate:\(testCase.JulianDate), julian_string:\(testCase.julian_string)")
    } else {
      res.num_ok += 1
    }
    var res_str: String = ""
    if cmp_time(d1: testCase.julian_string, d2: it) {
      res_str += "[JD]"
    }
    if cmp_time(d1: testCase.gregorian_string, d2: it) {
      res_str += "[GD]"
    }
    if res_str == "" {
      res_str = "Error"
      res.num_failed += 1
      res.errors.append("Both \(testCase.julian_string) and \(testCase.gregorian_string) != \(it)")
    } else {
      res.num_ok += 1
    }
    if dij != testCase.JulianDate {
      print(
        "Failed for JulianDate:\(testCase.JulianDate), dij:\(dij)"
      )
      res.num_failed += 1
      res.errors.append(
        "Failed for JulianDate:\(testCase.JulianDate), dij:\(dij)")
    } else {
      res.num_ok += 1
    }
  }
  return res
}

// get command line arguments:
let defaultFolder = "../../test_data"
let defaultCheckFailures = false
let defaultTestCases = "domain,time"
let args = CommandLine.arguments
let argc = args.count
// args: [swift_indrajala/indratest/.build/debug/indratest, --folder=../../test_data, --include_failure_cases=false, --test_cases=domain,time, --help]
// split at '=':
var folder = defaultFolder
var checkFailures = defaultCheckFailures
var testCases = defaultTestCases
for i in 1..<argc {
  let arg = args[i]
  let parts = arg.split(separator: "=")
  if parts.count == 2 {
    let key = parts[0]
    let value = parts[1]
    if key == "--folder" {
      folder = String(value)
    } else if key == "--include_failure_cases" {
      checkFailures = value == "true"
    } else if key == "--test_cases" {
      if value == "all" {
        testCases = "domain,time"
      } else {
        testCases = String(value)
      }
    } else {
      print("Unknown argument: \(key)")
      print(
        "Usage: indratest [--folder=../../test_data] [--include_failure_cases=false] [--test_cases=domain,time] [--help]"
      )
      exit(0)
    }
  } else {
    print(
      "Usage: indratest [--folder=../../test_data] [--include_failure_cases=false] [--test_cases=domain,time] [--help]"
    )
    exit(0)
  }
}

// Check if 'domain' is in testCases:
if testCases.contains("domain") || testCases == "all" {
  print("Testing domain with folder: \(folder)")
  let res_mq = test_mqcmp(folder: folder, checkFailures: checkFailures)
  print("#$#$# Result #$#$#")
  // serialize and print res_mq:
  let encoder = JSONEncoder()
  encoder.outputFormatting = .prettyPrinted
  do {
    let jsonData = try encoder.encode(res_mq)
    let jsonString = String(data: jsonData, encoding: .utf8)
    print(jsonString!)
  } catch {
    print("Failed to convert result to JSON: \(error)")
  }
}
if testCases.contains("time") || testCases == "all" {
  print("Testing time with folder: \(folder)")
  let res_time = test_time(folder: folder, checkFailures: checkFailures)
  print("#$#$# Result #$#$#")
  // serialize and print res_time:
  let encoder = JSONEncoder()
  encoder.outputFormatting = .prettyPrinted
  do {
    let jsonData = try encoder.encode(res_time)
    let jsonString = String(data: jsonData, encoding: .utf8)
    print(jsonString!)
  } catch {
    print("Failed to convert result to JSON: \(error)")
  }
}
