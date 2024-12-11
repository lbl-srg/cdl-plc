within ModelicaTestCases.SingleBlocks.Reals;
model Add
  Buildings.Controls.OBC.CDL.Interfaces.RealInput u2
    annotation (Placement(transformation(extent={{-140,-40},{-100,0}})));
  Buildings.Controls.OBC.CDL.Interfaces.RealOutput y1
    annotation (Placement(transformation(extent={{100,-20},{140,20}})));
  Buildings.Controls.OBC.CDL.Interfaces.RealInput u1
    annotation (Placement(transformation(extent={{-140,0},{-100,40}})));
  Buildings.Controls.OBC.CDL.Reals.Add add2
    annotation (Placement(transformation(extent={{-8,-10},{12,10}})));
equation
  connect(u1, add2.u1) annotation (Line(points={{-120,20},{-18,20},{-18,6},{-10,
          6}}, color={0,0,127}));
  connect(u2, add2.u2) annotation (Line(points={{-120,-20},{-18,-20},{-18,-6},{
          -10,-6}}, color={0,0,127}));
  connect(add2.y, y1)
    annotation (Line(points={{14,0},{120,0}},              color={0,0,127}));
  annotation (Icon(coordinateSystem(preserveAspectRatio=false)), Diagram(
        coordinateSystem(preserveAspectRatio=false)));
end Add;
