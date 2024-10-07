// swift-tools-version: 5.8
// The swift-tools-version declares the minimum version of Swift required to build this package.

import PackageDescription

let package = Package(
  name: "indralib",
  products: [
    // Products define the executables and libraries a package produces, making them visible to other packages.
    .library(
      name: "indralib",
      targets: ["indralib"])
  ],
  //dependencies: [
  //  // Dev dependencies
  //  .package(url: "https://github.com/apple/swift-docc-plugin", from: "1.4.3")
  //],
  targets: [
    // Targets are the basic building blocks of a package, defining a module or a test suite.
    // Targets can depend on other targets in this package and products from dependencies.
    .target(
      name: "indralib"),
    .testTarget(
      name: "indralibTests",
      dependencies: ["indralib"]),
  ]  //,
  //swiftLanguageVersions: [.version("6")]
)
