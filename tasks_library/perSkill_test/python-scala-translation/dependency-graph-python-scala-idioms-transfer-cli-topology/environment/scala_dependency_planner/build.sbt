ThisBuild / scalaVersion := "2.13.12"

lazy val root = (project in file(".")).settings(
  name := "dependency-planner-probe",
  libraryDependencies ++= Seq(
    "com.lihaoyi" %% "ujson" % "3.3.1"
  )
)
