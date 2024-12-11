within ModelicaTestCases.CompositeBlocks;
model Custom03
  "Custom implementation of a P controller with variable output limiter"

  parameter Real k = 2 "Constant gain";

  Buildings.Controls.OBC.CDL.Reals.MultiplyByParameter gain(k=1)
    annotation (Placement(transformation(extent={{-22,0},{-2,20}})));
  Buildings.Controls.OBC.CDL.Interfaces.RealInput ymax
    "Maximum value of output signal"
    annotation (Placement(transformation(extent={{-148,4},{-108,44}})));
  Buildings.Controls.OBC.CDL.Interfaces.RealOutput y "Maximum value of output signal"
    annotation (Placement(transformation(extent={{92,-26},{112,-6}}),
        iconTransformation(extent={{100,-10},{120,10}})));
  Buildings.Controls.OBC.CDL.Interfaces.RealOutput y1
                                                     "Maximum value of output signal"
    annotation (Placement(transformation(extent={{90,-88},{110,-68}}),
        iconTransformation(extent={{100,-10},{120,10}})));
equation

  connect(ymax,gain. u) annotation (Line(points={{-128,24},{-32,24},{-32,10},{
          -24,10}}, color={0,0,127}));
  connect(gain.y,y)
    annotation (Line(points={{0,10},{88,10},{88,-16},{102,-16}},
                                                             color={0,0,127}));
  connect(gain.y, y1) annotation (Line(points={{0,10},{88,10},{88,-64},{100,-64},
          {100,-78}}, color={0,0,127}));
  annotation (Icon(coordinateSystem(preserveAspectRatio=false)), Diagram(
        coordinateSystem(preserveAspectRatio=false)));
end Custom03;
