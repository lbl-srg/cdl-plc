within ModelicaTestCases.CompositeBlocks;
model Custom02
  "Custom implementation of a P controller with variable output limiter"

  parameter Real k = 2 "Constant gain";

  Buildings.Controls.OBC.CDL.Reals.MultiplyByParameter gain(k=1)
    annotation (Placement(transformation(extent={{-8,16},{12,36}})));
  Buildings.Controls.OBC.CDL.Interfaces.RealInput ymax
    "Maximum value of output signal"
    annotation (Placement(transformation(extent={{-134,20},{-94,60}})));
  Buildings.Controls.OBC.CDL.Interfaces.RealOutput y "Maximum value of output signal"
    annotation (Placement(transformation(extent={{106,-10},{126,10}}),
        iconTransformation(extent={{100,-10},{120,10}})));
  Buildings.Controls.OBC.CDL.Reals.MultiplyByParameter gain1(k=1)
    annotation (Placement(transformation(extent={{-10,-46},{10,-26}})));
  Buildings.Controls.OBC.CDL.Interfaces.RealInput ymax1
    "Maximum value of output signal"
    annotation (Placement(transformation(extent={{-136,-42},{-96,-2}})));
  Buildings.Controls.OBC.CDL.Interfaces.RealOutput y1
                                                     "Maximum value of output signal"
    annotation (Placement(transformation(extent={{104,-72},{124,-52}}),
        iconTransformation(extent={{100,-10},{120,10}})));
equation

  connect(ymax,gain. u) annotation (Line(points={{-114,40},{-18,40},{-18,26},{
          -10,26}}, color={0,0,127}));
  connect(gain.y,y)
    annotation (Line(points={{14,26},{102,26},{102,0},{116,0}},
                                                             color={0,0,127}));
  connect(ymax1, gain1.u) annotation (Line(points={{-116,-22},{-20,-22},{-20,
          -36},{-12,-36}}, color={0,0,127}));
  connect(gain1.y, y1) annotation (Line(points={{12,-36},{100,-36},{100,-62},{
          114,-62}}, color={0,0,127}));
  annotation (Icon(coordinateSystem(preserveAspectRatio=false)), Diagram(
        coordinateSystem(preserveAspectRatio=false)));
end Custom02;
