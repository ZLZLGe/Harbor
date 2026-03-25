ThisBuild / scalaVersion := "2.13.15"
ThisBuild / version := "0.1.0"

libraryDependencies ++= Seq(
  "io.circe" %% "circe-core" % "0.14.10",
  "io.circe" %% "circe-parser" % "0.14.10",
  "io.circe" %% "circe-generic" % "0.14.10"
)

Compile / run / fork := true
