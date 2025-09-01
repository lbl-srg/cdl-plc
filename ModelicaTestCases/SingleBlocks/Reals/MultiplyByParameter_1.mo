within ModelicaTestCases.SingleBlocks.Reals;
model MultiplyByParameter_1
  Buildings.Controls.OBC.CDL.Interfaces.RealInput u2
    annotation (Placement(transformation(extent={{-140,-20},{-100,20}})));
  Buildings.Controls.OBC.CDL.Reals.MultiplyByParameter gain(final k=1)
    annotation (Placement(transformation(extent={{-6,-10},{14,10}})));
  Buildings.Controls.OBC.CDL.Interfaces.RealOutput y1
    annotation (Placement(transformation(extent={{100,-20},{140,20}})));
equation
  connect(u2, gain.u) annotation (Line(points={{-120,0},{-8,0}},
                     color={0,0,127}));
  connect(gain.y, y1) annotation (Line(points={{16,0},{120,0}},
                 color={0,0,127}));
  annotation (Icon(coordinateSystem(preserveAspectRatio=false)), Diagram(
        coordinateSystem(preserveAspectRatio=false)));
end MultiplyByParameter_1;
