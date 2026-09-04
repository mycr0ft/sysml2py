/* Cruise-controller state machine — simulation demo.
 *
 *   sysmlpy sim examples/sim/cruise_controller.sysml
 *
 * Guards evaluate against the model's attribute values; try:
 *   sysmlpy sim examples/sim/cruise_controller.sysml \
 *       --run "Engage; SpeedOK; Decel; SpeedOK; Off; Cancel" --set speed=70
 */
package Sim {
    attribute speed : ScalarValues::Real := 30;
    attribute key : ScalarValues::Boolean := true;

    action def logState;
    action def hold;

    state def Cruise {
        entry; then off;
        state off;
        state engaged;
        state holding;
        state slowing;
        transition engage first off accept Engage when key do logState then engaged;
        transition hold first engaged accept SpeedOK do hold then holding;
        transition slow first holding accept Decel when speed > 40 do logState then slowing;
        transition resume first slowing accept SpeedOK then holding;
        transition stop first holding accept Off when speed <= 5 then off;
        transition cancel first engaged accept Cancel then off;
    }
}
