-- An owned required return is a case. It is not a posted payment and it does not bypass a refund cap.

ALTER TABLE assistance_exceptions DROP CONSTRAINT assistance_exceptions_kind_check;
ALTER TABLE assistance_exceptions ADD CONSTRAINT assistance_exceptions_kind_check
  CHECK (kind IN ('resident_overpayment', 'agency_delay', 'review', 'required_return'));
