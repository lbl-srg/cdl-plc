within ModelicaTestCases.SingleBlocks.Reals;
model PID
  Buildings.Controls.OBC.CDL.Interfaces.RealInput u_s
    annotation (Placement(transformation(extent={{-140,0},{-100,40}})));
  Buildings.Controls.OBC.CDL.Interfaces.RealInput u_m
    annotation (Placement(transformation(extent={{-140,-82},{-100,-42}})));
  Buildings.Controls.OBC.CDL.Interfaces.RealOutput y
    annotation (Placement(transformation(extent={{100,-20},{140,20}})));
  Buildings.Controls.OBC.CDL.Reals.PID conPID(
    k=1,
    Ti=100,
    yMax=1,
    yMin=0,
    reverseActing=true)
    annotation (Placement(transformation(extent={{-10,-10},{10,10}})));
equation
  connect(u_s, conPID.u_s) annotation (Line(points={{-120,20},{-22,20},{-22,0},
          {-12,0}}, color={0,0,127}));
  connect(u_m, conPID.u_m)
    annotation (Line(points={{-120,-62},{0,-62},{0,-12}}, color={0,0,127}));
  connect(conPID.y, y)
    annotation (Line(points={{12,0},{120,0}}, color={0,0,127}));
  annotation (Icon(coordinateSystem(preserveAspectRatio=false)), Diagram(
        coordinateSystem(preserveAspectRatio=false)));
end PID;
