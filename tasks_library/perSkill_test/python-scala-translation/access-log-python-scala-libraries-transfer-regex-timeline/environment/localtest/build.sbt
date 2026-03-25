ThisBuild / scalaVersion := "2.13.15"
ThisBuild / version := "0.1.0"

Compile / run / fork := true

scalacOptions ++= Seq(
  "-deprecation",
  "-feature",
  "-unchecked"
)
